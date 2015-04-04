import itertools
from ZEO.StorageServer import ZEOStorage, StorageServer
from ZEO.ClientStorage import ClientStorage
from ZEO.runzeo import ZEOServer
from ZEO.runzeo import ZEOOptions
from ZEO.Exceptions import ClientDisconnected


class ZEOBatchStorage(ZEOStorage):
    """
    ZEOStorage which loadEx object can return many oids at once
    """

    def loadBulk(self, oids):
        """ Load multiple oids """
        return [self.loadEx(oid) for oid in oids]

    extensions = ZEOStorage.extensions + [loadBulk]


class BatchStorageServer(StorageServer):
    ZEOStorageClass = ZEOBatchStorage


class ZEOBatchServer(ZEOServer):
    def create_server(self):
        storages = self.storages
        options = self.options
        self.server = BatchStorageServer(
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


class BatchClientStorage(ClientStorage):
    """
    Allows to get objects in batches
    zlibstorage should wrap *after* this
    """

    def __init__(self, *args, **kw):
        super(BatchClientStorage, self).__init__(*args, **kw)
        self._load_oids = {}

    def _process_invalidations(self, tid, oids):
        for oid in oids:
            if self._load_oids.get(oid, None):
                self._load_oids[oid] = 0
            self._cache.invalidate(oid, tid)
        self._cache.setLastTid(tid)

        if self._db is not None:
            self._db.invalidate(tid, oids)

    def loadBulk(self, oids):
        """
        Storage API to return multiple objects
        We load a unique set of them, just in case
        """
        oids = set(oids)

        # First, try to get whatever possible from cache
        self._load_lock.acquire()
        try:
            self._lock.acquire()    # for atomic processing of invalidations
            try:
                result = []
                for oid in oids:
                    out = self._cache.load(oid)
                    if not out:
                        self._load_oids[oid] = 1
                    else:
                        result.append(out)
            finally:
                self._lock.release()
            if len(self._load_oids) == 0:
                return result
            # If we ever get here, we need to load some more stuff
            # self._load_oids dictionary is protected by self._load_lock

            if self._server is None:
                raise ClientDisconnected()

            load_oids = self._load_oids.keys()

            # [(data, tid), (data, tid), ...]
            bulk_data = self._server.rpc.call('loadBulk', load_oids)

            for oid, (data, tid) in itertools.izip(load_oids, bulk_data):
                self._lock.acquire()    # for atomic processing of invalidations
                try:
                    if self._load_oids[oid]:  # Update cache only when there was no invalidation
                        self._cache.store(oid, tid, None, data)
                    del self._load_oids[oid]
                    result.append((data, tid))  # XXX shouldn't we provide a recent value from cache then?
                finally:
                    self._lock.release()
        finally:
            self._load_lock.release()

        return result


def zeoserver_main(args=None):
    options = ZEOOptions()
    options.realize(args=args)
    s = ZEOBatchServer(options)
    s.main()


if __name__ == "__main__":
    zeoserver_main()
