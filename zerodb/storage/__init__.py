import six

import ZEO.ClientStorage
from itertools import chain
from persistent import Persistent

from . import transforming
import logging

# TODO when it comes to the point we need to,
# we'll have to configure which classes to use
# with Zope interfaces

class ClientStorage(ZEO.ClientStorage.ClientStorage):

    def get_root_id(self):
        return self._call('get_root_id')

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
    TransformingStorage = kw.pop(
        'transforming_storage', transforming.TransformingStorage)
    debug = kw.pop("debug", False)
    return TransformingStorage(ClientStorage(sock, *args, **kw),
                               debug=debug)


def prefetch(objs):
    """
    Bulk-fetch ZODB objects
    """
    objs = [o for o in objs if getattr(o, "_p_oid", None)]
    if objs and objs[0]._p_jar:
        objs[0]._p_jar.prefetch(objs)


def prefetch_trees(trees, depth=10, bucket_types=(), shallow=True):
    """
    Bulk-fetch specified trees or buckets in logarithmic number of steps
    """
    trees = [t for t in trees
             if isinstance(t, Persistent) and hasattr(t, "_p_oid")]

    if len(trees) == 0 or depth == 0:
        # If someone inserts an infinite loop, we shouldn't go for that
        return

    prefetch(trees)

    if not bucket_types:
        bucket_types = tuple(set(chain(*[
            (type(t), t._bucket_type) for t in trees
            if hasattr(t, "_bucket_type")])))

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
        to_fetch = list(set(
            t for t in trees
            if isinstance(t, Persistent) and getattr(t, "_p_oid", None)
            ))

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
