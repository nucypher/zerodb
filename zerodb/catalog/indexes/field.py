from repoze.catalog.indexes.field import CatalogFieldIndex as _CatalogFieldIndex
from zerodb import trees
from zerodb.catalog.indexes.common import CallableDiscriminatorMixin
from zerodb.storage import prefetch


class CatalogFieldIndex(CallableDiscriminatorMixin, _CatalogFieldIndex):
    family = trees.family32

    # TODO prefetch in search method before multiunion
    # Pass data through apply method

    def __init__(self, discriminator):
        self._init_discriminator(discriminator)
        self._not_indexed = self.family.IF.Set()
        self.clear()

    def applyInRange(self, start, end, excludemin=False, excludemax=False):
        # prefetch is a catalog or None
        values = self._fwd_index.values(start, end, excludemin=excludemin, excludemax=excludemax)
        prefetch(values)
        return self.family.IF.multiunion(values)
