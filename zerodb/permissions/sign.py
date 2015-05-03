import BTrees
import persistent
import struct
import time
import transaction
import ZODB
from os import path
from ZEO.auth.base import Client
from ZEO.auth import register_module
from ZEO.Exceptions import AuthError
from ZODB import FileStorage

from zerodb.crypto import rand, sha256, sha512
from zerodb.crypto import ecc
from zerodb.intid import IdStore as BaseIdStore
from zerodb.storage import ServerStorage


class IdStore(BaseIdStore):
    family = BTrees.family32


class User(persistent.Persistent):
    """
    Persistent class to store users
    """

    def __init__(self, username, pubkey, realm="ZEO", administrator=False):
        """
        :param str username: Username
        :param str pubkey: ECC public key
        :param str realm: Authentication realm
        :param bool administrator: Whether it is a super-user (can create
            trees for others)
        """
        self.username = username
        self.pubkey = pubkey
        self.realm = realm
        self.administrator = administrator


def session_key(h_up, nonce):
    return sha512(h_up + ":" + nonce)


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
            root["users"] = IdStore()  # uid -> user
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
                username, pub = line.strip().split(":", 1)
                username = username.strip()
                pub = pub.strip().decode("hex")
                if username not in usernames:
                    user = User(username, pub, self.realm, administrator=True)
                    uid = users.add(user)
                    usernames[username] = uid
                else:
                    uid = usernames[username]
                    users[uid].pub = pub
                    users[uid].realm = self.realm

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
        users = self.db_root["users"]
        usernames = self.db_root["usernames"]
        if username in usernames:
            raise LookupError("User %s already exists" % username)
        with transaction.manager:
            user = User(username, pubkey, self.realm,
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
        with transaction.manager:
            uid = usernames[username]
            users[uid].pubkey = pubkey

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


class StorageClass(ServerStorage):
    def set_database(self, database):
        """
        :param PermissionsDatabase database: Database
        """
        assert isinstance(database, PermissionsDatabase)
        self.database = database
        self.noncekey = database.noncekey

    def _get_time(self):
        """Return a string representing the current time."""
        t = int(time.time())
        return struct.pack("i", t)

    def _get_nonce(self):
        s = ":".join([
            str(self.connection.addr),
            self._get_time(),
            self.noncekey])
        return sha256(s)

    def auth_get_challenge(self):
        """Return realm, challenge, and nonce."""
        self._challenge = rand(32)
        self._key_nonce = self._get_nonce()
        return self.auth_realm, self._challenge, self._key_nonce

    def auth_response(self, resp):
        # verify client response
        username, challenge, resp_sig = resp

        assert self._challenge == challenge

        user = self.database[username]
        verkey = ecc.public(user.pubkey)

        h_up = sha256("%s:%s:%s" % (username, self.database.realm, user.pubkey))

        # regeneration resp from user, password, and nonce
        check = sha256("%s:%s" % (h_up, challenge))
        verify = verkey.verify(resp_sig, check)
        if verify:
            self.connection.setSessionKey(session_key(h_up, self._key_nonce))
        return self._finish_auth(verify)

    extensions = [auth_get_challenge, auth_response]


class ECCClient(Client):
    extensions = ["auth_get_challenge", "auth_response"]

    def start(self, username, realm, password):
        priv = ecc.private(password)
        _realm, challenge, nonce = self.stub.auth_get_challenge()
        # _realm is str, challenge is 32-byte hash, nonce as well
        if _realm != realm:
            raise AuthError("expected realm %r, got realm %r"
                            % (_realm, realm))
        h_up = sha256("%s:%s:%s" % (username, realm, priv.get_pubkey()))

        check = sha256("%s:%s" % (h_up, challenge))
        sig = priv.sign(check)
        result = self.stub.auth_response((username, challenge, sig))
        if result:
            return session_key(h_up, nonce)
        else:
            return None


def register_auth():
    register_module("ecc_auth", StorageClass, ECCClient, PermissionsDatabase)
