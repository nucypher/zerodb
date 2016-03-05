from BTrees.Length import Length
from zope.index.text.lexicon import Lexicon as _Lexicon

from zerodb import trees
from zerodb.storage import parallel_traversal


def _text2list(text):
    # Helper: splitter input may be a string or a list of strings
    # Fixed from zope.index.text.lexicon
    try:
        text + u""
    except UnicodeDecodeError:
        try:
            return [text.decode("utf-8")]
        except UnicodeDecodeError:
            # It wasn't utf-8. But at least, it was text!
            return [text]
    except TypeError:
        return text
    else:
        return [text]


class Lexicon(_Lexicon):
    family = trees.family32  # In comparison with standard Lexicon, use bigger buckets

    def __init__(self, *pipeline):
        self._wids = self.family.OI.BTree()
        self._words = self.family.IO.BTree()
        self.wordCount = Length()
        self._pipeline = pipeline

    def sourceToWordIds(self, text):
        if text is None:
            text = ''
        last = _text2list(text)
        for element in self._pipeline:
            last = element.process(last)
        if not isinstance(self.wordCount, Length):
            # Make sure wordCount is overridden with a BTrees.Length.Length
            self.wordCount = Length(self.wordCount())
        # Strategically unload the length value so that we get the most
        # recent value written to the database to minimize conflicting wids
        # Because length is independent, this will load the most
        # recent value stored, regardless of whether MVCC is enabled
        self.wordCount._p_deactivate()
        parallel_traversal(self._wids, last)
        return list(map(self._getWordIdCreate, last))

    def termToWordIds(self, text):
        last = _text2list(text)
        for element in self._pipeline:
            last = element.process(last)
        wids = []
        if len(last) > 1:
            parallel_traversal(self._wids, last)
        for word in last:
            wids.append(self._wids.get(word, 0))
        return wids

    # XXX globToWordIds should pre-fetch prefixes in *range*
