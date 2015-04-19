from repoze.catalog.indexes.field import CatalogFieldIndex as _CatalogFieldIndex
from zerodb import trees


class CatalogFieldIndex(_CatalogFieldIndex):
    family = trees.family32

    # TODO prefetch in search method beore multiunion
    # Pass data through apply method

    def applyGe(self, min_value, prefetch=None):
        return self.applyInRange(min_value, None, prefetch=prefetch)

    def applyLe(self, max_value, prefetch=None):
        return self.applyInRange(None, max_value, prefetch=prefetch)

    def applyGt(self, min_value, prefetch=None):
        return self.applyInRange(min_value, None, excludemin=True, prefetch=prefetch)

    def applyLt(self, max_value, prefetch=None):
        return self.applyInRange(None, max_value, excludemax=True, prefetch=prefetch)

    def applyInRange(self, start, end, excludemin=False, excludemax=False, prefetch=None):
        # prefetch is a catalog or None
        values = self._fwd_index.values(start, end, excludemin=excludemin, excludemax=excludemax)
        if prefetch and values:
            prefetch._p_jar._db._storage.loadBulk([i._p_oid for i in values])
        return self.family.IF.multiunion(values)
