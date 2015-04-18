from repoze.catalog.catalog import Catalog as _Catalog
from zerodb import trees


class Catalog(_Catalog):
    family = trees.family32
