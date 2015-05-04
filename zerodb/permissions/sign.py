import BTrees
import persistent
import struct
import time
import transaction
import ZODB
from os import path
from ZEO.auth.base import Client
from ZEO.auth import register_module
from ZEO.Exceptions import AuthError, StorageError
from ZODB.POSException import POSKeyError
from ZODB import FileStorage
from ZODB.DB import z64
from ZODB.DB import DB as BaseDB
from ZODB.Connection import Connection as BaseConnection
from ZODB.Connection import RootConvenience

from zerodb.crypto import rand, sha256, sha512
from zerodb.crypto import ecc
from zerodb.intid import IdStore as BaseIdStore
from zerodb.storage import ServerStorage


class AccessDeniedError(StorageError):
    """Attempt to see encrypted data of others"""


class IdStore(BaseIdStore):
    family = BTrees.family32


class User(persistent.Persistent):
    """
    Persistent class to store users
    """

    def __init__(self, username, pubkey, realm="ZEO", administrator=False, root=None):
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


def create_root(storage, oid=z64, check_new=True):
    """This is copied from ZODB.DB.DB.__init__"""
    from ZODB.DB import Pickler, BytesIO, _protocol
    if check_new:
        try:
            storage.load(oid, '')
            return
        except KeyError:
            pass
    # Create the database's root in the storage if it doesn't exist
    from persistent.mapping import PersistentMapping
    root = PersistentMapping()
    # Manually create a pickle for the root to put in the storage.
    # The pickle must be in the special ZODB format.
    file = BytesIO()
    p = Pickler(file, _protocol)
    p.dump((root.__class__, None))
    p.dump(root.__getstate__())
    t = transaction.Transaction()
    t.description = 'initial database creation'
    storage.tpc_begin(t)
    storage.store(oid, None, file.getvalue(), '', t)
    storage.tpc_vote(t)
    storage.tpc_finish(t)


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

    def setup_delegation(self):
        # We use insert a hook to create a no-write root here
        ServerStorage.setup_delegation(self)
        create_root(self.storage)

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
        # This class is per-connection, so we're safe to assign attributes
        authenticated = self._finish_auth(verify)
        if authenticated:
            user_id = self.database.db_root["usernames"][username]
            self.user_id = struct.pack(self.database.uid_pack, user_id)
        return authenticated

    def _check_permissions(self, data, oid=None):
        if not data.endswith(self.user_id):
            raise AccessDeniedError("Attempt to access encrypted data of others at <%s>" % oid)

    def loadEx(self, oid):
        data, tid = ServerStorage.loadEx(self, oid)
        self._check_permissions(data, oid)
        return data, tid

    def storea(self, oid, serial, data, id):
        try:
            old_data, old_tid = ServerStorage.loadEx(self, oid)
            self._check_permissions(old_data, oid)
        except POSKeyError:
            pass  # We store a new one
        data += self.user_id
        return ServerStorage.storea(self, oid, serial, data, id)

    def loadBulk(self, oids):
        results = ServerStorage.load(self, oids)
        for data, _ in results:
            self._check_permissions(data, oid)
        return results

    def get_root_id(self):
        """
        Gets 8-byte private root ID. Creates it if it doesn't exist.
        :return: <root_id>, <is root new>?
        :rtype: str, bool
        """
        uid = struct.unpack(self.database.uid_pack, self.user_id)[0]
        user = self.database.db_root["users"][uid]
        if user.root:
            return user.root, False
        else:
            return self.storage.new_oid(), True

    # We certainly need to implement more methods for storage in here:
    # loadEx, loadBefore, deleteObject, storea, restorea, storeBlobEnd, storeBlobShared,
    # sendBlob, loadSerial, loadBulk

    extensions = [auth_get_challenge, auth_response, get_root_id]


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


# XXX should be in Connection which is in DB.klass

# XXX following classes should be somewhere else, they don't belong here
class Connection(BaseConnection):
    @property
    def root(self):
        return RootConvenience(self.get(self._db._root_oid))


import six
import threading
import warnings
from ZODB.DB import ConnectionPool, KeyedConnectionPool, IMVCCStorage,\
        BytesIO, Pickler, _protocol


class DB(BaseDB):
    klass = Connection
    # TODO make serious change to __init__ here:
    # Create *private* root and save its oid
    # Use saved root oid after that

    # The __init__ method is largely replication of original ZODB.DB.DB.__init__
    # with the exception of root creation
    def __init__(self, storage,
                 pool_size=7,
                 pool_timeout=(1 << 31),
                 cache_size=400,
                 cache_size_bytes=0,
                 historical_pool_size=3,
                 historical_cache_size=1000,
                 historical_cache_size_bytes=0,
                 historical_timeout=300,
                 database_name='unnamed',
                 databases=None,
                 xrefs=True,
                 large_record_size=(1 << 24),
                 **storage_args):
        """Create an object database.

        :Parameters:
          - `storage`: the storage used by the database, e.g. FileStorage
          - `pool_size`: expected maximum number of open connections
          - `cache_size`: target size of Connection object cache
          - `cache_size_bytes`: target size measured in total estimated size
               of objects in the Connection object cache.
               "0" means unlimited.
          - `historical_pool_size`: expected maximum number of total
            historical connections
          - `historical_cache_size`: target size of Connection object cache for
            historical (`at` or `before`) connections
          - `historical_cache_size_bytes` -- similar to `cache_size_bytes` for
            the historical connection.
          - `historical_timeout`: minimum number of seconds that
            an unused historical connection will be kept, or None.
          - `xrefs` - Boolian flag indicating whether implicit cross-database
            references are allowed
        """
        if isinstance(storage, six.string_types):
            import ZODB.FileStorage
            storage = ZODB.FileStorage.FileStorage(storage, **storage_args)
        elif storage is None:
            import ZODB.MappingStorage
            storage = ZODB.MappingStorage.MappingStorage(**storage_args)
        import ZODB  # Where did it go??

        # Allocate lock.
        x = threading.RLock()
        self._a = x.acquire
        self._r = x.release

        # pools and cache sizes
        self.pool = ConnectionPool(pool_size, pool_timeout)
        self.historical_pool = KeyedConnectionPool(historical_pool_size,
                                                   historical_timeout)
        self._cache_size = cache_size
        self._cache_size_bytes = cache_size_bytes
        self._historical_cache_size = historical_cache_size
        self._historical_cache_size_bytes = historical_cache_size_bytes

        # Setup storage
        self.storage = storage
        self.references = ZODB.serialize.referencesf
        try:
            storage.registerDB(self)
        except TypeError:
            storage.registerDB(self, None)  # Backward compat

        if (not hasattr(storage, 'tpc_vote')) and not storage.isReadOnly():
            warnings.warn(
                "Storage doesn't have a tpc_vote and this violates "
                "the storage API. Violently monkeypatching in a do-nothing "
                "tpc_vote.",
                DeprecationWarning, 2)
            storage.tpc_vote = lambda *args: None

        if IMVCCStorage.providedBy(storage):
            temp_storage = storage.new_instance()
        else:
            temp_storage = storage
        try:
            oid, new = temp_storage.get_root_id()
            if new:
                create_root(temp_storage, oid=oid, check_new=False)
            self._root_oid = oid
        finally:
            if IMVCCStorage.providedBy(temp_storage):
                temp_storage.release()

        # Multi-database setup.
        if databases is None:
            databases = {}
        self.databases = databases
        self.database_name = database_name
        if database_name in databases:
            raise ValueError("database_name %r already in databases" %
                             database_name)
        databases[database_name] = self
        self.xrefs = xrefs

        self.large_record_size = large_record_size


def register_auth():
    register_module("ecc_auth", StorageClass, ECCClient, PermissionsDatabase)
