import itertools as it

from repoze.catalog.indexes.field import CatalogFieldIndex as _CatalogFieldIndex
from zerodb import trees
from zerodb.catalog.indexes.common import CallableDiscriminatorMixin
from zerodb.storage import prefetch
from zerodb.util.iter import ListPrefetch


class CatalogFieldIndex(CallableDiscriminatorMixin, _CatalogFieldIndex):
    family = trees.family32

    # TODO prefetch in search method before multiunion
    # Pass data through apply method

    def __init__(self, discriminator):
        self._init_discriminator(discriminator)
        self._not_indexed = self.family.IF.Set()
        self.clear()

    def applyInRange(self, start, end, excludemin=False, excludemax=False):
        return ListPrefetch(lambda: it.chain.from_iterable(
            ListPrefetch(lambda: self._fwd_index.values(start, end, excludemin=excludemin, excludemax=excludemax))))
        # XXX what if these treesets are pretty deep? Need to pre-fetch "first N elements"

    def scan_forward(self, docids, limit=None):
        # Batch-prefetch treesets
        # If sorting index is the same as _fwd_index, we already pre-fetched
        # the same objects in the same order!
        fwd_index = ListPrefetch(lambda: self._fwd_index.values())

        n = 0
        for set in fwd_index:
            for docid in set:
                if docid in docids:
                    n += 1
                    yield docid
                    if limit and n >= limit:
                        raise StopIteration
