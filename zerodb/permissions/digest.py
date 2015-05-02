import BTrees
from passlib.hash import bcrypt_sha256 as passhash
import persistent
import transaction
import ZODB
from os import path
from ZODB import FileStorage

from zerodb.crypto import rand
from zerodb.intid import IdStore as BaseIdStore


class IdStore(BaseIdStore):
    family = BTrees.family32


class User(persistent.Persistent):
    """
    Persistent class to store users
    """

    def __init__(self, username, password_hash, realm="ZEO", administrator=False):
        """
        :param str username: Username
        :param str password_hash: Hash of password (using hashlib's encrypt/verify)
        :param str realm: Authentication realm
        :param bool administrator: Whether it is a super-user (can create
            trees for others)
        """
        self.username = username
        self.password_hash = password_hash
        self.realm = realm
        self.administrator = administrator


class PermissionsDatabase(object):
    """
    Class which represent permission storages:
    Config file with root users and ZODB db with others.

    ZODB db consists of two trees:
    str -> int: username -> user uid
    int -> obj: IdStore user uid -> User object

    When database is empty, we populate it with data for all users from
    config file.
    """
    realm = None
    passhash = passhash
    family = BTrees.family32

    def __init__(self, filename, realm=None):
        """
        :param str filename: Config file with users and their password hashes
        :param str realm: ZODB's default permissions realm
        """
        self.storage_filename = path.splitext(filename)[0] + ".db"
        self.db = ZODB.DB(FileStorage.FileStorage(self.storage_filename))
        self.db_conn = self.db.open()
        self.db_root = self.db_conn.root()
        root = self.db_root
        with transaction.manager:
            root["users"] = IdStore()  # uid -> user
            root["usernames"] = self.family.OI.BTree()  # username -> uid

        # Database.__init__
        self.filename = filename
        self.load()

        # Frankly speaking, this realm-based security is questionable
        # Keep it here for now
        if realm:
            if self.realm and self.realm != realm:
                raise ValueError("Specified realm %r differs from database "
                                 "realm %r" % (realm or '', self.realm))
            else:
                self.realm = realm

        # DigestDatabase.__init__
        self.noncekey = rand(8)  # should it really be only 8 bytes?? XXX

    def close(self):
        """
        Close connection to the database
        """
        self.db_conn.close()

    def load(self):
        """
        Load config file and fill the database if necessary.
        Password hash is updated if changed in file.
        If user is removed from file, it is left in the database.
        All users from the file are administrators.
        """
        filename = self.filename
        if not filename:
            return

        if not path.exists(filename):
            return

        fd = open(filename, "r")

        # If first line is realm, set it. Othewise they are all users
        try:
            line = fd.next()
            if line.startswith("realm "):
                self.realm = line.strip().split(" ", 1)[1]
            else:
                fd.seek(0)
        except StopIteration:
            return

        users = self.db_root["users"]
        usernames = self.db_root["usernames"]

        with transaction.manager:
            for line in fd:
                username, password_hash = line.strip().split(":", 1)
                username = username.strip()
                password_hash = password_hash.strip()
                if username not in usernames:
                    user = User(username, password_hash, self.realm,
                            administrator=True)
                    uid = users.add(user)
                    usernames[username] = uid
                else:
                    uid = usernames[username]
                    users[uid].password_hash = password_hash
                    users[uid].realm = self.realm

    def save(self, fd=None):
        """No need to save to the file. Compatibility with how ZODB does it"""
        pass

    def get_password(self, username):
        """
        Gets password hash from ZODB

        :param str username: Username

        :return: Password hash
        :rtype: str
        :raises LookupError: if user doesn't exist
        """
        usernames = self.db_root["usernames"]
        if username not in usernames:
            raise LookupError("No such user: %s" % username)
        uid = usernames[username]
        users = self.db_root["users"]
        return users[uid].password_hash

    def verify_password(self, username, password):
        """
        Verifies if password is correct

        :param str username: Username
        :param str password: Plain text password

        :return: was it correct?
        :rtype: bool
        :raises LookupError: if user doesn't exist
        """
        return self.passhash.verify(password, self.get_password(username))

    def add_user(self, username, password, administrator=False):
        """
        Add user to the database

        :param str username: Username
        :param str password: Password

        :raises LookupError: if username already exists
        """
        users = self.db_root["users"]
        usernames = self.db_root["usernames"]
        if username in usernames:
            raise LookupError("User %s already exists" % username)
        with transaction.manager:
            user = User(username, self.passhash.encrypt(password), self.realm,
                    administrator=administrator)
            uid = users.add(user)
            usernames[username] = uid

    def del_user(self, username):
        """
        Remove existing user from the db (only ZODB)

        :param str username: Username
        :raises LookupError: if user does not exist
        """
        users = self.db_root["users"]
        usernames = self.db_root["usernames"]
        if username not in usernames:
            raise LookupError("No such user: %s" % username)
        with transaction.manager:
            uid = usernames[username]
            del users[uid]
            del usernames[username]

    def change_password(self, username, password):
        """
        Change password of existing user

        :param str username: Username
        :param str password: Password

        :raises LookupError: if user does not exist
        """
        users = self.db_root["users"]
        usernames = self.db_root["usernames"]
        if username not in usernames:
            raise LookupError("No such user: %s" % username)
        with transaction.manager:
            uid = usernames[username]
            users[uid].password_hash = self.passhash.encrypt(password)

    def _store_password(self, username, password):
        """
        Store password of existing or non-existing user

        :param str username: Username
        :param str password: Password
        """
        if username in self.db_root["usernames"]:
            self.change_password(username, password)
        else:
            self.add_user(username, password)

    def __getitem__(self, username):
        """
        :param str username: Username
        :return: User object
        :rtype: User
        :raises LookupError: if user does not exist
        """
        users = self.db_root["users"]
        usernames = self.db_root["usernames"]
        uid = usernames[username]
        if username not in usernames:
            raise LookupError("No such user: %s" % username)
        return users[uid]
