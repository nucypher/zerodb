import six
from ZEO.StorageServer import StorageServer as BaseStorageServer
from ZEO.runzeo import ZEOServer as BaseZEOServer
from ZEO.runzeo import ZEOOptions
import ZEO.zrpc.error
from itertools import chain
from persistent import Persistent

from . import batch
from . import premade
from . import transforming
import logging

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
        options = ZEOOptions()
        options.realize(args=args)

        for o_storage in options.storages:
            if o_storage.config.pack_gc:
                logging.warn("Packing with GC and end-to-end encryption removes all the data")
                logging.warn("Turining GC off!")
                o_storage.config.pack_gc = False

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
    if six.PY2 and isinstance(sock, unicode):
        sock = str(sock)
    TransformingStorage = kw.pop('transforming_storage', transforming.TransformingStorage)
    debug = kw.pop("debug", False)
    return TransformingStorage(batch.BatchClientStorage(sock, *args, **kw), debug=debug)


def prefetch(objs):
    """
    Bulk-fetch ZODB objects
    """
    objs = [o for o in objs if hasattr(o, "_p_oid")]
    if objs:
        oids = [y._p_oid for y in objs if y._p_oid is not None]
        if objs[0]._p_jar:
            objs[0]._p_jar._db._storage.loadBulk(oids, returns=False)


def prefetch_trees(trees, depth=10, bucket_types=(), shallow=True):
    """
    Bulk-fetch specified trees or buckets in logarithmic number of steps
    """
    trees = [t for t in trees if isinstance(t, Persistent) and hasattr(t, "_p_oid")]

    if len(trees) == 0 or depth == 0:
        # If someone inserts an infinite loop, we shouldn't go for that
        return

    if shallow:  # For performance once we have everything in cache
        cache_load = trees[0]._p_jar._db._storage._cache.load
        if not [True for o in trees if cache_load(o._p_oid) is None]:
            return

    prefetch(trees)

    if not bucket_types:
        bucket_types = tuple(set(chain(*[(type(t), t._bucket_type) for t in trees if hasattr(t, "_bucket_type")])))

    children = []
    for tree in trees:
        state = tree.__getstate__()
        if state:
            children += [o for o in state[0] if isinstance(o, bucket_types)]

    prefetch_trees(children, depth=(depth - 1), bucket_types=bucket_types)


def btree_state_search(state, key):
    """
    Search in raw state of BTree.
    state = ((branch, key, branch, key, ... , key, branch), 1st_bucket) or None
    """
    if not state:
        return -1, None

    state = state[0]

    # Based on python BTree logic
    lo = 0
    hi = (len(state) + 1) // 2
    i = hi // 2
    while i > lo:
        i_key = state[i * 2 - 1]
        if i_key < key:
            lo = i
        elif i_key > key:
            hi = i
        else:
            break
        i = (lo + hi) // 2
    return i, state[i * 2]


def parallel_traversal(trees, keys):
    """
    Traverse trees in parallel to fill up cache
    """
    if not isinstance(trees, (list, tuple)):
        to_fetch = [trees]
        trees = [trees] * len(keys)
    else:
        to_fetch = list(set(t for t in trees if isinstance(t, Persistent) and hasattr(t, "_p_oid")))

    prefetch(to_fetch)

    nxt_trees = []
    nxt_keys = []
    for key, tree in zip(keys, trees):
        if isinstance(tree, Persistent) and hasattr(tree, "_bucket_type"):
            _, nxt = btree_state_search(tree.__getstate__(), key)
            if isinstance(nxt, (type(tree), tree._bucket_type)):
                nxt_keys.append(key)
                nxt_trees.append(nxt)

    if nxt_keys:
        parallel_traversal(nxt_trees, nxt_keys)
