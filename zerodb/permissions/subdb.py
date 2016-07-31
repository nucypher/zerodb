import mock
import ssl

import ZEO.asyncio.mtacceptor
import ZEO.Exceptions
import ZEO.runzeo
import ZEO.StorageServer
import ZODB

from .base import get_admin
from .ownerstorage import OwnerStorage

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

class ZEOStorage(ZEO.StorageServer.ZEOStorage):

    user_id = None

    registered_methods = frozenset(
        ZEO.StorageServer.registered_methods | set(['get_root_id']))

    def register(self, storage_id, read_only, credentials=None):
        super(ZEOStorage, self).register(storage_id, read_only)

        der = self.connection.transport.get_extra_info(
            'ssl_object').getpeercert(1)

        with ZODB.DB(self.storage).transaction() as conn:
            admin = get_admin(conn)
            self.user_id = admin.uids[der]
            if self.user_id is None:
                # Nobody cert.
                if not credentials:
                    raise ZEO.Exceptions.AuthError()

            if credentials:
                user = admin.users_by_name[credentials['name']]
                if ((user.id != self.user_id and self.user_id is not None) or
                    not user.check_password(credentials['password'])
                    ):
                    raise ZEO.Exceptions.AuthError()
                self.user_id = user.id

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
            if conn and zs.user_id == conn.user_id:
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
        options.realize(args)

        for o_storage in options.storages:
            if o_storage.config.pack_gc:
                logging.warn(
                    "Packing with GC and end-to-end encryption"
                    " removes all the data")
                logging.warn("Turining GC off!")
                o_storage.config.pack_gc = False

        s = cls(options)
        s.main()

