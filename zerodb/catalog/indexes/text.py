from copy import copy
from zope.index.text.lexicon import CaseNormalizer
from zope.index.text.lexicon import Lexicon
from zope.index.text.lexicon import Splitter
from zope.index.text.lexicon import StopWordRemover
from zope.index.text.okapiindex import OkapiIndex
from repoze.catalog.indexes.text import CatalogTextIndex as _CatalogTextIndex
from zerodb import trees


class CatalogTextIndex(_CatalogTextIndex):
    family = trees.family32

    def __init__(self, *args, **kw):
        kw = copy(kw)
        kw["lexicon"] = Lexicon(Splitter(), CaseNormalizer(), StopWordRemover())
        kw["index"] = OkapiIndex(kw["lexicon"], family=trees.family32)
        super(CatalogTextIndex, self).__init__(*args, **kw)
