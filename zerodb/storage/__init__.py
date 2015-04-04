from ZEO.StorageServer import StorageServer as BaseStorageServer
from ZEO.runzeo import ZEOServer as BaseZEOServer
from ZEO.runzeo import ZEOOptions

import batch


# TODO when it comes to the point we need to,
# we'll have to configure which classes to use
# with Zope interfaces

ServerStorage = batch.ZEOBatchStorage


class StorageServer(BaseStorageServer):
    ZEOStorageClass = ServerStorage


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
        options = ZEOOptions()
        options.realize(args=args)
        s = cls(options)
        s.main()
