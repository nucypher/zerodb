from repoze.catalog.indexes.field import CatalogFieldIndex as _CatalogFieldIndex
from zerodb import trees


class CatalogFieldIndex(_CatalogFieldIndex):
    family = trees.family32
