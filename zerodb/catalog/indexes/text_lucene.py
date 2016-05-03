import BTrees
import itertools
import logging

import six
from BTrees.Length import Length
from BTrees.OOBTree import TreeSet as SortedSet  # sorted set implemented in C
from collections import Counter, defaultdict
from itertools import islice
from six.moves import zip as izip, map as imap, xrange
from math import sqrt, log
from persistent import Persistent
from zope.interface import implementer
from zope.index.interfaces import IInjection
from zope.index.interfaces import IStatistics
from zope.index.text.interfaces import IExtendedQuerying
from zope.index.text.interfaces import ILexiconBasedIndex
from zope.index.text.queryparser import _tokenizer_regex

from zerodb.storage import prefetch, parallel_traversal
from zerodb.catalog.indexes.pwid import PersistentWid


class LengthyTree(object):
    def __init__(self, obj, L):
        """
        Replaces __len__ method to use Length, proxies all other methods.

        :param Persistent obj: tree-like object
        :param Length L: BTrees' Length object
        """
        self.__obj = obj
        self.__L = L

    def __len__(self):
        return self.__L.value

    def __getattr__(self, attr):
        return getattr(self.__obj, attr)

    def __iter__(self):
        return self.__obj.__iter__()


@implementer(IInjection, IStatistics, ILexiconBasedIndex, IExtendedQuerying)
class IncrementalLuceneIndex(Persistent):
    """
    Using Lucene's practical scoring function and incremental search
    """
    # Using Okapi index requires us to fetch all docids for all word ids.
    # That makes scalability of the search bad, even for a single keyword
    # This class uses Lucene's practical scoring function:
    # https://www.elastic.co/guide/en/elasticsearch/guide/current/practical-scoring-function.html

    # In brief, practical scoring is this:
    #   t - keyword (or term) which is searched
    #   D - document
    #   TF(t, D) = sqrt(f(t, D))
    #   IDF(t) = 1 + log(N_docs / (N_docs_for_term + 1))
    #   score(term, D) = TF * IDF**2 / sqrt(N_terms_in_D)
    #   score(D) = sum(score(term, D)) / sqrt(sum(IDF(t)**2))

    # When we search for one keyword, we can keep document UIDs
    # Ordered by w_t = TF(t, D) / sqrt(N_terms_in_D),
    # for example in a TreeSet((-w_t, uid)).
    # Reading it incrementally gives docs ordered from most to least relevant.

    # Now the harder part (not in Lucene)

    # When we want to do a multi-keyword search, it is, in a way, weighted union
    # of searches for all keywords.
    # E.g. now:
    #   w(D) = sum(w_t * IDF(t)**2)   // no need to normalize by sqrt(sum(idf**2))
    # weight calculation and sort in memory, which fetches docweights for all terms again.
    # This is slow when e2e encrypted and fetched remotely, and also reveals sum(N_docs_for_term) to the server

    # Here's how we do the same incrementally ("lazy")
    # We allow elements to be shifted by max_out_of_order = 3 from their ideal position.
    # We read beginnings of sorted lists of (w_i, uid_i) for each word.
    # After we calculate the sum,
    # w_j_known = sum(w_j * IDF(t_j)**2, t: all terms for which we know w_j for uid_i)

    # for i_th element the weight could be between:
    #   w_min_i(t_j) = sum(w_min(t_j) * IDF(t_j)**2: all terms for which we don't know w_j) + w_i_known
    #   and
    #   w_max_i(t_j) = sum(w_max(t_j) * IDF(t_j)**2: all terms for which we don't know w_j) + w_i_known

    # For each term, we have current window of docs ordered by weight which still haven't been returned.
    # It is likely that some term is particularly selective and largely outweights others,
    # E.g. for almost all elements in the current window, weight ranges (w_min_i, w_max_i) don't overlap
    # for different i. Or, perhaps, elements are misplaced by no more than max_out_of_order positions.

    # We choose a term for which all positions at the tail of the window can never appear within the limit # of docs.
    # If there are none, we expand most promising wid set by factor of 2 until we get this situation.
    # Out of those terms (if there are multiple), we select one which has smallest number of
    # doc uids misplaced.

    # For misplaced docids, we fetch their weights. Now we know order within the specified
    # number of documents.

    # For this to work, we need to keep
    # BTree(wids -> (TreeSet(w_i, uid_i), BTree(uid_i -> w_i), Length))
    # Length is for calculating IDF

    family = BTrees.family32
    lexicon = property(lambda self: self._lexicon,)
    # * index_doc
    # * unindex_doc
    # * clear
    # * documentCount
    # * wordCount
    # * lexicon
    # search
    # search_phrase
    # search_glob
    # _search_wids
    # * query_weight

    def __init__(self, lexicon, family=None, keep_phrases=True):
        if family is not None:
            self.family = family
        self._lexicon = lexicon
        self.keep_phrases = keep_phrases
        self.clear()

    def clear(self):
        # ._wordinfo = BTree(wids -> (TreeSet((weight, docid)), BTree(docid -> weight), Length))
        self._wordinfo = self.family.IO.BTree()

        # ._docwords = BTree(docid -> widcode)
        # used for document unindexing
        # but no phrase search
        self._docwords = self.family.IO.BTree()

        self.wordCount = Length()
        self.documentCount = Length()

    def _get_doctrees(self, wids):
        """
        Gets persistent objects used for indexes for wids
        returns: {wid -> TreeSet((weight, docid))}, {wid -> Length}
        """
        weights = {}
        lengths = {}
        parallel_traversal(self._wordinfo, wids)

        for wid in wids:
            record = self._wordinfo.get(wid)
            if record is None:
                length = Length(0)
                wdocid = self.family.OO.TreeSet()
                self._wordinfo[wid] = (wdocid, length)
                self.wordCount.change(1)
            else:
                wdocid, length = record

            weights[wid] = wdocid
            lengths[wid] = length

        return weights, lengths

    def get_words(self, docid):
        """Return a list of the wordids for a given docid."""
        return self._docwords[docid].decode_wid()

    def _get_widscores(self, ctr, docid, widlen=None):
        """
        Get scores per word:
            score = sqrt(f) / sqrt(widlen)

        :param dict ctr: Counter {wid -> number_of_wids}
        :param int widlen: Number of unique words in document. Use len(ctr) if
            not given
        :returns dict: {wid -> (-score, docid)}
        """
        widlen = sqrt(widlen or len(ctr))
        return {w: (-sqrt(f) / widlen, docid) for w, f in ctr.items()}

    def index_doc(self, docid, text):
        if docid in self._docwords:
            return self._reindex_doc(docid, text)

        wids = self._lexicon.sourceToWordIds(text)

        # XXX Counter is slow. If it is an issue, need to include C module
        # http://stackoverflow.com/questions/2522152/python-is-a-dictionary-slow-to-find-frequency-of-each-character
        widcnt = Counter(wids)
        widset = widcnt.keys()
        widcode = PersistentWid.encode_wid(wids if self.keep_phrases else widset)
        self._docwords[docid] = widcode

        if widset:
            weights, lengths = self._get_doctrees(widset)
            docscores = self._get_widscores(widcnt, docid)
            parallel_traversal(*zip(*[(weights[w], docscores[w]) for w in widset]))
            prefetch(list(lengths.values()) + [self.documentCount])

            for w in widset:
                weights[w].add(docscores[w])
                lengths[w].change(1)

        self.documentCount.change(1)

        return len(wids)

    def _reindex_doc(self, docid, text):
        # We should change Length only for new wids used
        old_wids = self.get_words(docid)
        old_ctr = Counter(old_wids)
        old_widset = set(old_ctr)
        new_wids = self._lexicon.sourceToWordIds(text)
        new_ctr = Counter(new_wids)
        new_widset = set(new_ctr)
        removed_wids = old_widset - new_widset
        added_wids = new_widset - old_widset
        all_wids = list(new_widset | old_widset)

        weights, lengths = self._get_doctrees(all_wids)

        for w in removed_wids:
            lengths[w].change(-1)
        for w in added_wids:
            lengths[w].change(1)

        old_docscores = self._get_widscores(old_ctr, docid)
        new_docscores = self._get_widscores(new_ctr, docid)
        parallel_traversal(*zip(*[
            (weights[w], old_docscores.get(w) or new_docscores.get(w))
            for w in all_wids]))
        # We should update all the weights if len(old_wids) != len(new_wids)
        # ...and that is generally the case, so we update always
        for w in old_widset:
            try:
                weights[w].remove(old_docscores[w])
            except KeyError:
                # This should never happen
                # If it does, it's a bad sign, though we should still work
                logging.error("Old weight-docid pair not found!")
        for w in new_widset:
            weights[w].add(new_docscores[w])

        self._docwords[docid] = PersistentWid.encode_wid(new_wids if self.keep_phrases else new_widset)

        return len(new_wids)

    def unindex_doc(self, docid):
        if docid not in self._docwords:
            return
        wids = self.get_words(docid)
        ctr = Counter(wids)
        wids = list(ctr)
        weights, lengths = self._get_doctrees(wids)
        scores = self._get_widscores(ctr, docid)
        parallel_traversal(*zip(*[(weights[w], scores[w]) for w in wids]))
        for w in wids:
            lengths[w].change(-1)
            weights[w].remove(scores[w])
            if lengths[w].value == 0:
                del self._wordinfo[w]
        del self._docwords[docid]
        self.documentCount.change(-1)

    def idf2(self, wid):
        """
        Returns IDF squared.
        Note that definition of IDF is different from the classic one
        """
        N_docs = self.documentCount.value
        N_for_term = self._wordinfo[wid][1].value
        return (1.0 + log(N_docs / (1.0 + N_for_term))) ** 2

    def _remove_oov_wids(self, wids):
        parallel_traversal(self._wordinfo, set(wids))
        return filter(self._wordinfo.has_key, wids)

    def query_weight(self, terms):
        """
        terms - string with terms or list with wids

        Normalization factor:
            sum of idfs squared (with number-of-uses coefficient)
        """
        if isinstance(terms, list):
            wc = Counter(terms)
        else:
            wc = Counter(self._lexicon.termToWordIds(terms))
        if 0 in wc:
            del wc[0]
        wids = self._remove_oov_wids(wc.keys())
        return sum([self.idf2(w) * wc[w] for w in wids])

    def _search_wids(self, wids):
        """
        Finds pointers to iterables (-score, docid) for wids in order,
        IDFs squared are also calculated as weights
        """
        return [(LengthyTree(*self._wordinfo[w]), self.idf2(w)) for w in wids]

    def search(self, term):
        wids = self._lexicon.termToWordIds(term)
        wids = self._remove_oov_wids(wids)
        if not wids:
            return []
        return mass_weightedUnion(self._search_wids(wids))

    def search_glob(self, pattern):
        wids = self._lexicon.globToWordIds(pattern.lower())
        wids = self._remove_oov_wids(wids)
        return mass_weightedUnion(self._search_wids(wids))

    def _search_all(self, term):
        tokens = [t.lower() for t in _tokenizer_regex.findall(term)]
        glob_cond = lambda t: ('?' in t) or ('*' in t)
        glob_tokens = filter(glob_cond, tokens)
        word_tokens = filter(lambda t: not glob_cond(t), tokens)
        wids = set()
        wids.update(self._lexicon.termToWordIds(word_tokens))
        wids.update(itertools.chain(*map(self._lexicon.globToWordIds, glob_tokens)))
        wids = self._remove_oov_wids(wids)
        # XXX
        # We should have OrderedDict-like lazy objects
        # and we should have weightedIntersection and weightedUnion
        # working lazily in a for of zerodbext.catalog
        # This is just a workaround for simpler queries
        # XXX
        return imap(lambda x: x[0], mass_weightedUnion(self._search_wids(wids)))

    def search_phrase(self, phrase):
        # Need to do mass_weightedIntersection here.
        # Simplest version of it would be:
        #   fetch (score, docid) info for the rarest keyword
        #   find same docids in different keywords
        #   do intersection in memory
        #   fetch widcode to search for phrase
        # XXX we'd require to maintain also BTree(docid -> score)
        raise NotImplementedError


def mass_weightedUnion(L):
    """
    Incremental version of mass_weightedUnion
    :param list L: (TreeSet((-score, docid)), weight) elements
    :returns: iterable ordered from large to small sum(score*weight)
    """
    cache_size = 40
    order_size = 15
    order_violation = 3
    cache_updated = None

    if len(L) == 0:
        return

    elif len(L) == 1:
        # Trivial
        tree, weight = L[0]
        # XXX need to make it possible to advance the tree N elements ahead!
        for (score, docid) in tree:
            yield (docid, -score * weight)

    else:
        # XXX make into an iterator class

        trees, weights = zip(*L)
        prefetch(trees)
        prefetch([x._firstbucket for x in trees if x._firstbucket is not None])

        unread_max = [-t.minKey()[0] * w for t, w in L]
        lengths = map(len, trees)
        iters = dict(enumerate(map(iter, trees)))
        caches = [{} for i in range(len(L))]
        docid2cacheid = defaultdict(list)
        cache_len = None
        maxscores = [-1] * len(L)
        used = set()
        sorted_mins = SortedSet()  # Contains tuples (-min_weight, docid)
        mins_dict = {}  # {docid -> min_weight}
        docids = []

        def precache(i, size):
            try:
                for j in xrange(size):
                    score, docid = next(iters[i])
                    score = -score * weights[i]
                    if unread_max[i] > score:
                        unread_max[i] = score
                    if docid not in used:
                        caches[i][docid] = score
                        docid2cacheid[docid].append(i)
                        if maxscores[i] < 0:
                            maxscores[i] = score

                        # documents are not repeated in iterators
                        # it means that for the iterator i we didn't meet docid before
                        # which means that we should just add score to the current minscore
                        total_score = mins_dict.get(docid, 0.0) + score
                        if docid in mins_dict:
                            sorted_mins.remove((-mins_dict[docid], docid))
                        mins_dict[docid] = total_score
                        sorted_mins.add((-total_score, docid))
            except StopIteration:
                del iters[i]
                unread_max[i] = 0

        while True:
            # Main cycle in which we yield values to make an iterator

            # Advance iterators when needed / fill caches to keep them long enough
            # Perhaps, some better algorithm is needed to pre-read, this is the simplest

            cache_updated = False
            for i in list(iters.keys()):
                cache = caches[i]
                if len(cache) < cache_size / 2:
                    precache(i, cache_size - len(cache))
                    cache_len = sum(map(len, caches))
                    cache_updated = True

            if cache_updated or (cache_len is not None and (cache_len > order_violation) and (len(docids) < order_violation)):
                while True:
                    max_sum = sum(unread_max)
                    mins = []
                    docids = []
                    maxs = []
                    for w, docid in islice(iter(sorted_mins), order_size):
                        mins.append(-w)
                        docids.append(docid)
                        cacheids = docid2cacheid[docid]
                        # Slower equivalent:
                        # maxs = sum(c.get(docid, m) for c, m in izip(caches, unread_max))
                        # because
                        # -w   = sum(c.get(docid, 0) for c, m in izip(caches, unread_max))
                        maxs.append(max_sum - sum(unread_max[i] for i in cacheids) - w)
                    violated = False
                    for i in xrange(len(mins) - order_violation - 1):
                        # Naive implementation. Can go from tail and do faster
                        # in batches of size of order_violation
                        for m in maxs[i + order_violation:]:
                            if m > mins[i]:
                                violated = True
                                break
                        if violated:
                            break
                    if len(mins) == order_size:
                        # Last check: can the order be violated by out-of-cache elements?
                        if mins[len(mins) - order_violation] < max_sum:
                            violated = True
                    if not violated:
                        break
                    else:
                        # XXX instead we could download enough elements to change
                        # sum(unread_max) by much enough
                        # We need something like "advance_to" method
                        precache(
                                max(enumerate(m / max(l - len(c), 1) for m, l, c in izip(unread_max, lengths, caches)), key=lambda x: x[1])[0],
                                cache_size / 2)
                        cache_len = sum(map(len, caches))

            if not docids:
                break
            minw = mins.pop(0)
            maxw = maxs.pop(0)
            docid = docids.pop(0)
            for i, c in enumerate(caches):
                if docid in c:
                    if c[docid] == unread_max[i]:
                        del c[docid]
                        unread_max[i] = max(six.itervalues(c))
                    else:
                        del c[docid]
                    cache_len -= 1
            used.add(docid)
            sorted_mins.remove((-minw, docid))
            del mins_dict[docid]
            yield docid, (minw + maxw) / 2.0
