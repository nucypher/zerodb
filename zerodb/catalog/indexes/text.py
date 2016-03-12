from zope.index.text import TextIndex as ZopeTextIndex
from zope.index.text.lexicon import CaseNormalizer
from zope.index.text.lexicon import Splitter
from zope.index.text.lexicon import StopWordRemover
from zerodbext.catalog.indexes.text import CatalogTextIndex as _CatalogTextIndex

from zerodb import trees
from zerodb.catalog.indexes.common import CallableDiscriminatorMixin
from zerodb.util.iter import Sliceable

from .text_lexicon import Lexicon
from .text_lucene import IncrementalLuceneIndex
from .text_okapi import OkapiIndex


class CatalogTextIndex(CallableDiscriminatorMixin, _CatalogTextIndex):
    family = trees.family32
    index_class = IncrementalLuceneIndex

    def __init__(self, discriminator, lexicon=None, index=None):
        self._init_discriminator(discriminator)

        self._not_indexed = self.family.IF.Set()

        lexicon = lexicon or Lexicon(Splitter(), CaseNormalizer(), StopWordRemover())
        index = index or self.index_class(lexicon, family=self.family)

        ZopeTextIndex.__init__(self, lexicon, index)
        self.clear()

    def apply(self, querytext, start=0, count=None):
        # For now, let's parse querytext ourselves
        # and later make the queryparser capable to be iterative
        if hasattr(self.index, "_search_all"):
            return Sliceable(lambda: self.index._search_all(querytext))
        else:
            return super(CatalogTextIndex, self).apply(
                    querytext, start=start, count=count)


class CatalogTextIndexOkapi(CatalogTextIndex):
    index_class = OkapiIndex
