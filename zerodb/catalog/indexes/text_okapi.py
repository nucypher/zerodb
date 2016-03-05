import itertools

from BTrees.Length import Length
from zope.index.text.okapiindex import OkapiIndex as _OkapiIndex

from zerodb import trees
from zerodb.storage import prefetch_trees, parallel_traversal
from zerodb.catalog.indexes.pwid import PersistentWid


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
        # self._wordinfo - IOBTree of docid -> weight trees
        get_doc2score = self._wordinfo.get
        new_word_count = 0

        # Fill up cache for performance over the network
        wids = wid2weight.keys()
        parallel_traversal(self._wordinfo, wids)
        parallel_traversal(map(get_doc2score, wids), [docid] * len(wids))

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

    def index_doc(self, docid, text):
        if docid in self._docwords:
            return self._reindex_doc(docid, text)
        wids = self._lexicon.sourceToWordIds(text)
        wid2weight, docweight = self._get_frequencies(wids)
        self._mass_add_wordinfo(wid2weight, docid)
        self._docweight[docid] = docweight
        self._docwords[docid] = PersistentWid.encode_wid(wids)
        try:
            self.documentCount.change(1)
        except AttributeError:
            # upgrade documentCount to Length object
            self.documentCount = Length(len(self._docweight))
        count = len(wids)
        self._change_doc_len(count)
        return count

    def _reindex_doc(self, docid, text):
        # Touch as few docid->w(docid, score) maps in ._wordinfo as possible.
        self._change_doc_len(-self._docweight[docid])

        old_wids = self.get_words(docid)
        old_wid2w, old_docw = self._get_frequencies(old_wids)

        new_wids = self._lexicon.sourceToWordIds(text)
        new_wid2w, new_docw = self._get_frequencies(new_wids)

        old_widset = self.family.IF.TreeSet(old_wid2w.keys())
        new_widset = self.family.IF.TreeSet(new_wid2w.keys())

        IF = self.family.IF
        in_both_widset = IF.intersection(old_widset, new_widset)
        only_old_widset = IF.difference(old_widset, in_both_widset)
        only_new_widset = IF.difference(new_widset, in_both_widset)
        del old_widset, new_widset

        for wid in only_old_widset.keys():
            self._del_wordinfo(wid, docid)

        for wid in only_new_widset.keys():
            self._add_wordinfo(wid, new_wid2w[wid], docid)

        for wid in in_both_widset.keys():
            # For the Okapi indexer, the "if" will trigger only for words
            # whose counts have changed.  For the cosine indexer, the "if"
            # may trigger for every wid, since W(d) probably changed and
            # W(d) is divided into every score.
            newscore = new_wid2w[wid]
            if old_wid2w[wid] != newscore:
                self._add_wordinfo(wid, newscore, docid)

        self._docweight[docid] = new_docw
        self._docwords[docid] = PersistentWid.encode_wid(new_wids)
        return len(new_wids)

    def get_words(self, docid):
        """Return a list of the wordids for a given docid."""
        return self._docwords[docid].decode_wid()

    def _search_wids(self, wids):
        # Bulk-fetch all the info we want to use
        if len(wids) > 1:
            parallel_traversal(self._wordinfo, wids)
        prefetch_trees([self._wordinfo[wid] for wid in wids])

        docids = list(set(itertools.chain(
            *[self._wordinfo[wid].keys() for wid in wids])))
        if len(docids) > 1:
            parallel_traversal(self._docweight, docids)

        return super(OkapiIndex, self)._search_wids(wids)
