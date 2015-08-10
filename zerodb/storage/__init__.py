from ZEO.StorageServer import StorageServer as BaseStorageServer
from ZEO.runzeo import ZEOServer as BaseZEOServer
from ZEO.runzeo import ZEOOptions
import ZEO.zrpc.error
from Crypto.Random import atfork

import batch
import premade
import transforming

# TODO when it comes to the point we need to,
# we'll have to configure which classes to use
# with Zope interfaces

ServerStorage = premade.DefaultServerStorage


class StorageServer(BaseStorageServer):
    ZEOStorageClass = ServerStorage

    def invalidate(self, conn, storage_id, tid, invalidated=(), info=None):
        """ Internal: broadcast info and invalidations to clients. """

        # Same as in the base class
        if invalidated:
            invq = self.invq[storage_id]
            if len(invq) >= self.invq_bound:
                invq.pop()
            invq.insert(0, (tid, invalidated))

        for p in self.connections[storage_id]:
            if getattr(p, 'user_id', None) == getattr(conn, 'user_id', None):
                try:
                    if invalidated and p is not conn:
                        p.client.invalidateTransaction(tid, invalidated)
                    elif info is not None:
                        p.client.info(info)
                except ZEO.zrpc.error.DisconnectedError:
                    pass


class ZEOServer(BaseZEOServer):
    def create_server(self):
        storages = self.storages
        options = self.options
        self.server = StorageServer(
            options.address,
            storages,
            read_only=options.read_only,
            invalidation_queue_size=options.invalidation_queue_size,
            invalidation_age=options.invalidation_age,
            transaction_timeout=options.transaction_timeout,
            monitor_address=options.monitor_address,
            auth_protocol=options.auth_protocol,
            auth_database=options.auth_database,
            auth_realm=options.auth_realm)

    @classmethod
    def run(cls, args=None):
        atfork()
        options = ZEOOptions()
        options.realize(args=args)
        s = cls(options)
        s.main()


def client_storage(sock, *args, **kw):
    """
    Storage client

    :param sock: UNIX or TCP socket
    :param cipher: Encryptor to use (see zerodb.crypto)
    :param bool debug: Output debug messages to the log
    :param transforming_storage: Wrapper-storage to use (TransformingStorage)
    :returns: Storage
    :rtype: TransformingStorage
    """
    if type(sock) is unicode:
        sock = str(sock)
    TransformingStorage = kw.pop('transforming_storage', transforming.TransformingStorage)
    debug = kw.pop("debug", False)
    return TransformingStorage(batch.BatchClientStorage(sock, *args, **kw), debug=debug)


def prefetch(objs):
    """
    Bulk-fetch ZODB objects
    """
    objs = filter(lambda x: hasattr(x, "_p_oid"), objs)
    if objs:
        oids = [y._p_oid for y in objs]
        if objs[0]._p_jar:
            objs[0]._p_jar._db._storage.loadBulk(oids)
