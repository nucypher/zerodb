import BTrees
import hashlib
import persistent
import six
import transaction
import ZODB

from os import path
from ZODB import FileStorage
from ZEO import auth

from zerodb.crypto import rand
from zerodb.intid import IdStore as BaseIdStore
from zerodb.permissions.elliptic import __module_name__ as default_auth


class IdStore(BaseIdStore):
    family = BTrees.family32


class User(persistent.Persistent):
    """
    Persistent class to store users
    """

    def __init__(
            self, username, pubkey, realm="ZEO",
            administrator=False, root=None, auth_method=None):
        """
        :param str username: Username
        :param str pubkey: ECC public key
        :param str realm: Authentication realm
        :param bool administrator: Whether it is a super-user (can create
            trees for others)
        :param str root: Oid of root of the tree. Could be None or 8-byte string
        """
        self.username = username
        self.pubkey = pubkey
        self.realm = realm
        self.administrator = administrator
        self.root = root
        self.auth_method = auth_method


def session_key(h_up, nonce):
    return hashlib.sha512(h_up + b":" + nonce).digest()


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
    family = BTrees.family32
    uid_pack = "i"  # family32 -> "i", family64 -> "q"

    def __init__(self, filename, realm=None):
        """
        :param str filename: Config file with users and their password hashes
        :param str realm: ZODB's default permissions realm
        """
        self.storage_filename = path.splitext(filename)[0] + ".db"
        self.storage = FileStorage.FileStorage(self.storage_filename)
        self.db = ZODB.DB(self.storage)
        self.db_conn = self.db.open()
        self.db_root = self.db_conn.root()
        root = self.db_root
        with transaction.manager:
            if "users" not in root:
                root["users"] = IdStore()  # uid -> user
            if "usernames" not in root:
                root["usernames"] = self.family.OI.BTree()  # username -> uid

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

        self.noncekey = rand(32)

    def close(self):
        """
        Close connection to the database
        """
        self.db_conn.close()
        self.storage.close()

    def load(self):
        """
        Load config file and fill the database if necessary.
        Public key is updated if changed in file.
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
            line = next(fd)
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
                auth_method, username, pub = line.strip().split(":", 2)
                username = username.strip()
                if six.PY2:
                    pub = pub.strip().decode("hex")
                else:
                    pub = bytes.fromhex(pub.strip())
                if username not in usernames:
                    user = User(
                            username, pub, self.realm, administrator=True,
                            auth_method=auth_method)
                    uid = users.add(user)
                    usernames[username] = uid
                else:
                    uid = usernames[username]
                    users[uid].pub = pub
                    users[uid].realm = self.realm
                    users[uid].auth_method = auth_method

    def save(self, fd=None):
        """No need to save to the file. Compatibility with how ZODB does it"""
        pass

    def add_user(self, username, pubkey, administrator=False):
        """
        Add user to the database

        :param str username: Username
        :param str pubkey: ECC public key

        :raises LookupError: if username already exists
        """
        # XXX when we start authenticating with certificates,
        # we'll be more smart about this
        assert default_auth in auth._auth_modules
        auth_method = default_auth

        users = self.db_root["users"]
        usernames = self.db_root["usernames"]
        if username in usernames:
            raise LookupError("User %s already exists" % username)

        if transaction.manager._txn:
            commit = False
        else:
            commit = True
            transaction.begin()

        user = User(
                username, pubkey, self.realm, administrator=administrator,
                auth_method=auth_method)
        uid = users.add(user)
        usernames[username] = uid

        if commit:
            transaction.commit()

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

        if transaction.manager._txn:
            commit = False
        else:
            commit = True
            transaction.begin()

        uid = usernames[username]
        del users[uid]
        del usernames[username]

        if commit:
            transaction.commit()

    def change_key(self, username, pubkey):
        """
        Change password of existing user

        :param str username: Username
        :param str pubkey: ECC public key

        :raises LookupError: if user does not exist
        """
        users = self.db_root["users"]
        usernames = self.db_root["usernames"]
        if username not in usernames:
            raise LookupError("No such user: %s" % username)

        if transaction.manager._txn:
            commit = False
        else:
            commit = True
            transaction.begin()

        uid = usernames[username]
        users[uid].pubkey = pubkey

        if commit:
            transaction.commit()

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
