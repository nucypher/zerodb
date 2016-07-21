import mock
import ssl

from ZODB.utils import maxtid, u64, z64
from ZODB.POSException import POSKeyError, StorageError
import ZEO.asyncio.mtacceptor
import ZEO.runzeo
import ZEO.StorageServer
import ZODB
import ZODB.interfaces
import zope.interface

from .base import get_admin

class Acceptor(ZEO.asyncio.mtacceptor.Acceptor):

    def __init__(self, storage_server, addr, ssl):
        super(Acceptor, self).__init__(storage_server, addr, ssl)
        [self.cert_storage_id] = storage_server.storages # TCBOO
        storage = storage_server.storages[self.cert_storage_id]
        self.cert_db = ZODB.DB(storage)
        self.invalidate = self.cert_db._mvcc_storage.invalidate
        with self.cert_db.transaction() as conn:
            self.certs_oid = get_admin(conn).certs._p_oid

    @property
    def ssl_context(self):
        context = self.storage_server.create_ssl_context()
        with self.cert_db.transaction() as conn:
            certs = conn.get(self.certs_oid)
            context.load_verify_locations(cadata=certs.data)
        return context

    @ssl_context.setter
    def ssl_context(self, context):
        pass

@zope.interface.implementer(ZODB.interfaces.IMultiCommitStorage)
class OwnerStorage(object):
    """Storage wrapper that adds/stript/checks owner id in record

    Some special considerations around bootstrapping:

    - Except for the root users, users' ids are their root folder's
      oids.  This allows us to grant access even when a user's root
      folder was written by the root user.  Note that once a user
      modified their root folder, the root user won't have access.

    - All user can access object 0, but they can't access any
      persistent subobjects of it.
    """

    # methods we punt on:
    history = load = restore = iterator = undo = undoLog = undoInfo = None
    record_iternext = storeBlob = loadBlob = restoreBlob = None
    def __iter__(self):
        if False: yield
    def supportsUndo(self):
        return False

    def __init__(self, storage, user_id):
        self.user_id = user_id
        self.storage = storage

    def __getattr__(self, name):
        return getattr(self.storage, name)

    def _check_permissions(self, data, oid=None):
        if not (
            data.endswith(self.user_id) or
            oid == self.user_id or
            oid == z64
            ):
            raise StorageError(
                "Attempt to access encrypted data of others at <%s> by <%s>" % (
                    u64(oid), u64(self.user_id)))

    def loadBefore(self, oid, tid):
        r = self.storage.loadBefore(oid, tid)
        if r is not None:
            data, serial, after = r
            self._check_permissions(data, oid)
            return data[:-len(self.user_id)], serial, after
        else:
            return r

    def loadSerial(self, oid, serial):
        r = self.storage.loadSerial(oid, tid)
        data = self.storage.loadSerial(self, oid, serial)
        self._check_permissions(data, oid)
        return data[:-len(self.user_id)]

    def store(self, oid, serial, data, version, transaction):
        try:
            old_data = self.storage.loadBefore(oid, maxtid)[0]
            self._check_permissions(old_data, oid)
        except POSKeyError:
            pass  # We store a new one
        data += self.user_id
        self.storage.store(oid, serial, data, version, transaction)

    def __len__(self):
        return len(self.storage)

class ZEOStorage(ZEO.StorageServer.ZEOStorage):

    user_id = None

    registered_methods = frozenset(
        ZEO.StorageServer.registered_methods | set(['get_root_id']))

    def register(self, storage_id, read_only):
        super(ZEOStorage, self).register(storage_id, read_only)

        der = self.connection.transport.get_extra_info(
            'ssl_object').getpeercert(1)

        with ZODB.DB(self.storage).transaction() as conn:
            self.user_id = get_admin(conn).uids[der]

        self.storage = OwnerStorage(self.storage, self.user_id)

    def setup_delegation(self):
        super(ZEOStorage, self).setup_delegation()
        self.connection.methods = self.registered_methods

    def get_root_id(self):
        return self.user_id

class StorageServer(ZEO.StorageServer.StorageServer):

    def invalidate(self, conn, storage_id, tid, invalidated=(), info=None):
        """ Internal: broadcast info and invalidations to clients. """

        # Same as in the base class
        if invalidated:
            invq = self.invq[storage_id]
            if len(invq) >= self.invq_bound:
                invq.pop()
            invq.insert(0, (tid, invalidated))

        for zs in self.zeo_storages_by_storage_id[storage_id]:
            if zs.user_id == conn.user_id:
                connection = zs.connection
                if invalidated and zs is not conn:
                    # zs.client.invalidateTransaction(tid, invalidated)
                    connection.call_soon_threadsafe(
                        connection.async,
                        'invalidateTransaction', tid, invalidated)
                elif info is not None:
                    # zs.client.info(info)
                    connection.call_soon_threadsafe(
                        connection.async, 'info', info)

        # Update the cert storage db:
        if storage_id == self.acceptor.cert_storage_id:
            self.acceptor.invalidate(tid, invalidated)

    def create_client_handler(self):
        return ZEOStorage(self, self.read_only)


class ZeroDBOptions(ZEO.runzeo.ZEOOptions):

    def realize(self, *args):
        # Evil evil hack, but ZConfig schemas hurt and we need to
        # ovverride the way ssl configuration is handled. :(
        with mock.patch('ssl.create_default_context'):
            super(ZeroDBOptions, self).realize(*args)


class ZEOServer(ZEO.runzeo.ZEOServer):
    def create_server(self):
        storages = self.storages
        options = self.options
        self.server = StorageServer(
            options.address,
            storages,
            read_only=options.read_only,
            client_conflict_resolution=True,
            invalidation_queue_size=options.invalidation_queue_size,
            invalidation_age=options.invalidation_age,
            transaction_timeout=options.transaction_timeout,
            Acceptor=Acceptor,
            )

        # See evil evil mock hack above :(
        ssl_args, ssl_kw_args = options.ssl.load_cert_chain.call_args
        def create_ssl_context():
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(*ssl_args, **ssl_kw_args)
            context.verify_mode = ssl.CERT_REQUIRED
            return context

        self.server.create_ssl_context = create_ssl_context

    @classmethod
    def run(cls, args=None):
        options = ZeroDBOptions()
        options.realize(args=args)

        for o_storage in options.storages:
            if o_storage.config.pack_gc:
                logging.warn(
                    "Packing with GC and end-to-end encryption"
                    " removes all the data")
                logging.warn("Turining GC off!")
                o_storage.config.pack_gc = False

        s = cls(options)
        s.main()

