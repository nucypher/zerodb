from repoze.catalog.indexes.field import CatalogFieldIndex as _CatalogFieldIndex
from zerodb import trees
from zerodb.storage import prefetch


class CatalogFieldIndex(_CatalogFieldIndex):
    family = trees.family32

    # TODO prefetch in search method beore multiunion
    # Pass data through apply method

    def applyInRange(self, start, end, excludemin=False, excludemax=False):
        # prefetch is a catalog or None
        values = self._fwd_index.values(start, end, excludemin=excludemin, excludemax=excludemax)
        prefetch(values)
        return self.family.IF.multiunion(values)
