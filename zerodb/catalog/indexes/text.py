from BTrees.Length import Length
from zope.index.text import TextIndex as ZopeTextIndex
from zope.index.text.lexicon import CaseNormalizer
from zope.index.text.lexicon import Lexicon as _Lexicon
from zope.index.text.lexicon import Splitter
from zope.index.text.lexicon import StopWordRemover
from zope.index.text.okapiindex import OkapiIndex as _OkapiIndex
from repoze.catalog.indexes.text import CatalogTextIndex as _CatalogTextIndex
from zerodb import trees
from zerodb.catalog.indexes.common import CallableDiscriminatorMixin
from zerodb.storage import prefetch


class Lexicon(_Lexicon):
    family = trees.family32  # In comparison with standard Lexicon, use bigger buckets

    def __init__(self, *pipeline):
        self._wids = self.family.OI.BTree()
        self._words = self.family.IO.BTree()
        self.wordCount = Length()
        self._pipeline = pipeline

    # TODO ideally, we should do parallel traversal here, however this tree is small, so ok for now


class OkapiIndex(_OkapiIndex):

    def clear(self):
        # wid -> {docid -> weight}; t -> D -> w(D, t)
        self._wordinfo = trees.family32.IO.BTree()
        # XXX
        # Scalability of this Zope's approach is pretty bad (esp. when many documents).
        # Following is needed:
        # _wordinfo = BTree of (word, weight, docid) - TreeSet could be used instead
        # searching a keyword will be as _wordinfo.keys((word_start, None, None)),
        # already sorted by weight (just has to be multiplied by idf)
        # this works for both search and glob_search
        # However, when searching multiple keywords,
        # Need to find an efficient (logarithmic) algorithm of
        # incremental, weighted set intersection
        # Even without efficient intersection, it is faster and more secure anyway
        # XXX

        # docid -> weight
        self._docweight = self.family.IF.BTree()

        # docid -> WidCode'd list of wids (~1/4 of document size)
        # Used for un-indexing, and for phrase search.
        self._docwords = self.family.IO.BTree()

        # Use a BTree length for efficient length computation w/o conflicts
        self.wordCount = Length()
        self.documentCount = Length()

    def _mass_add_wordinfo(self, wid2weight, docid):
        dicttype = type({})
        get_doc2score = self._wordinfo.get
        new_word_count = 0

        # oids of all dictionaries (or BTree tops) to prefetch
        # do we get them? - test
        prefetch(map(get_doc2score, wid2weight.keys()))

        for wid, weight in wid2weight.items():
            doc2score = get_doc2score(wid)
            if doc2score is None:
                doc2score = {}
                new_word_count += 1
            elif (isinstance(doc2score, dicttype) and
                  len(doc2score) == self.DICT_CUTOFF):
                doc2score = self.family.IF.BTree(doc2score)
            doc2score[docid] = weight
            self._wordinfo[wid] = doc2score  # not redundant:  Persistency!
        try:
            self.wordCount.change(new_word_count)
        except AttributeError:
            # upgrade wordCount to Length object
            self.wordCount = Length(len(self._wordinfo))


class CatalogTextIndex(CallableDiscriminatorMixin, _CatalogTextIndex):
    family = trees.family32

    def __init__(self, discriminator, lexicon=None, index=None):
        self._init_discriminator(discriminator)

        self._not_indexed = self.family.IF.Set()

        lexicon = lexicon or Lexicon(Splitter(), CaseNormalizer(), StopWordRemover())
        index = index or OkapiIndex(lexicon, family=self.family)

        ZopeTextIndex.__init__(self, lexicon, index)
        self.clear()
