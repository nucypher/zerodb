"""
StorageServer which provides granular access to zodb based on auth info
"""

# from ZEO.StorageServer import ZEOStorage, StorageServer
from ZEO.auth.auth_digest import StorageClass as AuthStorageClass
from ZEO.auth import register_module
from ZEO.auth.auth_digest import DigestClient
from ZEO.auth.auth_digest import DigestDatabase, hexdigest
from ZODB import FileStorage
import ZODB
import logging
import persistent
import transaction
from os import path
from BTrees import OOBTree

log = logging.getLogger(__name__)


class User(persistent.Persistent):

    def __init__(self, username, password_hash, realm="ZEO", administrator=False):
        self.username = username
        self.password_hash = password_hash
        self.realm = realm
        self.administrator = administrator


class PermissionsDatabase(DigestDatabase):
    """
    zodb: iobtree, oobtree (int -> obj, str -> int)
    (open or create zodb database) and open passwords file.
    Sync users/passwords file => zodb.
    permissions: private by default.
    create subtrees when create users or read file / not in zodb.
    """
    realm = None

    def __init__(self, filename, realm=None):
        self.storage_filename = path.splitext(filename)[0] + ".db"
        self.db = ZODB.DB(FileStorage.FileStorage(self.storage_filename))
        self.db_conn = self.db.open()
        self.db_root = self.db_conn.root()
        root = self.db_root
        with transaction.manager:
            root["users"] = OOBTree.OOBTree()
        DigestDatabase.__init__(self, filename, realm=realm)

    def _hash_password(self, username, password):
        return hexdigest("%s:%s:%s" % (username, self.realm, password))

    def load(self):
        filename = self.filename
        if not filename:
            return

        if not path.exists(filename):
            return

        fd = open(filename)
        L = fd.readlines()

        if not L:
            return

        if L[0].startswith("realm "):
            line = L.pop(0).strip()
            self.realm = line[len("realm "):]

        users = self.db_root["users"]
        with transaction.manager:
            for line in L:
                username, password_hash = line.strip().split(":", 1)
                if username not in users:
                    user = User(username, password_hash.strip(), self.realm)
                    users[username] = user
                else:
                    users[username].password_hash = password_hash.strip()
                    users[username].realm = self.realm

    def save(self, fd=None):
        """ No need to save to the file """
        pass

    def get_password(self, username):
        """Returns password hash for specified username.

        Callers must check for LookupError, which is raised in
        the case of a non-existent user specified."""
        users = self.db_root["users"]
        if username not in users:
            raise LookupError("No such user: %s" % username)
        return users[username].password_hash

    def add_user(self, username, password):
        users = self.db_root["users"]
        if username in users:
            raise LookupError("User %s already exists" % username)
        with transaction.manager:
            user = User(username, self._hash_password(username, password), self.realm)
            users[username] = user

    def del_user(self, username):
        users = self.db_root["users"]
        with transaction.manager:
            if username not in users:
                raise LookupError("No such user: %s" % username)
            del users[username]

    def change_password(self, username, password):
        users = self.db_root["users"]
        with transaction.manager:
            if username not in users:
                raise LookupError("No such user: %s" % username)
            users[username].password_hash = self._hash_password(username, password)


class PermittableZEOStorage(AuthStorageClass):

    def _check_permission(self, name, oid):
        print name, oid.encode("hex"), getattr(self, "username", None)
        return True

    def auth_response(self, resp):
        """
        Record username to the connection.
        We need to know it to figure out who reads what
        """

        result = AuthStorageClass.auth_response(self, resp)

        username = resp[0] if self.authenticated else None
        self.username = username

        return result

    def register(self, storage_id, read_only):
        AuthStorageClass.register(self, storage_id, read_only)
        print self.username, self.storage
        # Need to open db.
        # If user doesn't exist, create with a new id (locking the db)
        # Get the id, close connection, id goes to this class

    # methods
    # loadEx, loadBefore, deleteObject, storea, restorea, storeBlobEnd, storeBlobShared, sendBlob, loadSerial?
    # get_info shoud show auth support
    # need get_private_root and get_public_root
    # store with permissions, e.g. obj -> struct.pack("Q", user_id) + data -> xdata[:8] + xdata[8:]

    def loadEx(self, oid):
        if self._check_permission("loadEx", oid):
            return AuthStorageClass.loadEx(self, oid)

    def storea(self, oid, serial, data, id):
        if self._check_permission("storea", oid):
            return AuthStorageClass.storea(self, oid, serial, data, id)


def register_auth():
    register_module("permidigest", PermittableZEOStorage, DigestClient, PermissionsDatabase)
    # register_module("permidigest", PermittableZEOStorage, DigestClient, DigestDatabase)
