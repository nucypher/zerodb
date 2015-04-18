from copy import copy
from repoze.catalog.indexes.field import CatalogFieldIndex as _CatalogFieldIndex
from repoze.catalog.indexes.text import CatalogTextIndex as _CatalogTextIndex
from repoze.catalog.catalog import Catalog as _Catalog
from zope.index.text.lexicon import CaseNormalizer
from zope.index.text.lexicon import Lexicon
from zope.index.text.lexicon import Splitter
from zope.index.text.lexicon import StopWordRemover
from zope.index.text.okapiindex import OkapiIndex
from zerodb import trees


class Catalog(_Catalog):
    family = trees.family32


class CatalogFieldIndex(_CatalogFieldIndex):
    family = trees.family32


class CatalogTextIndex(_CatalogTextIndex):
    family = trees.family32

    def __init__(self, *args, **kw):
        kw = copy(kw)
        kw["lexicon"] = Lexicon(Splitter(), CaseNormalizer(), StopWordRemover())
        kw["index"] = OkapiIndex(kw["lexicon"], family=trees.family32)
        super(CatalogTextIndex, self).__init__(*args, **kw)
