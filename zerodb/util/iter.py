from itertools import islice, izip, imap
from cachetools import LRUCache


class Sliceable(object):
    def __init__(self, f, cache_size=1000, length=None):
        """
        Makes a sliceable, cached list-like interface to an iterator
        :param callable f: Function which inits the iterator
        """
        self.f = f
        self.cache = LRUCache(cache_size)
        self.stop = 0
        self.length = length
        self.iterator = f()

    def __iter__(self):
        return iter(self.f())

    def __len__(self):
        if self.length is None:
            if hasattr(self.iterator, "__len__"):
                return len(self.iterator)
            else:
                return len(list(self.f()))
        else:
            if callable(self.length):
                return self.length()
            else:
                return self.length

    def __getitem__(self, key):
        if isinstance(key, int) and (key >= 0):
            if key in self.cache:
                return self.cache[key]
            elif key < self.stop:
                self.stop = 0
                self.iterator = self.f()

            delta = key - self.stop
            result = islice(self.iterator, delta, delta + 1).next()
            self.cache[key] = result
            self.stop = key + 1
            return result

        elif isinstance(key, slice):
            if key.stop is None:
                # Whole sequence is asked
                return list(self.f())
            start = key.start or 0
            step = key.step or 1

            indexes = range(start, key.stop, step)
            index_upd = start
            while index_upd < key.stop and index_upd in self.cache:
                index_upd += step

            if index_upd < self.stop and index_upd < key.stop:
                self.iterator = self.f()
                result = list(islice(self.iterator, start, key.stop, step))
                for i, value in izip(indexes, result):
                    self.cache[i] = value
                self.stop = key.stop
                return result

            else:
                result = [self.cache[i] for i in xrange(start, index_upd, step)]
                if len(result) < len(indexes):
                    result_upd = list(islice(self.iterator, index_upd - self.stop, key.stop - self.stop, step))
                else:
                    result_upd = []
                for i, value in izip(indexes[len(result):], result_upd):
                    self.cache[i] = value
                self.stop = key.stop
                return result + result_upd

        else:
            raise KeyError("Key must be non-negative integer or slice, not {}"
                           .format(key))


class DBList(Sliceable):
    def __init__(self, query_f, db, **kw):
        """
        :param function query_f: Function which returns results of the query in format (size, uids)
        :param zerodb.DB db: Currend DB instance
        """
        self.db = db

        def get_object(uid):
            obj = db._objects[uid]
            obj._v_uid = uid
            return obj

        def f():
            self.length, it = query_f()
            return imap(get_object, it)

        super(DBList, self).__init__(f, **kw)


class DBListPrefetch(DBList):
    def __getitem__(self, key):
        previous_stop = self.stop
        result = super(DBListPrefetch, self).__getitem__(key)
        if self.stop != previous_stop:
            # Fetching objects needed
            if isinstance(result, list):
                self.db._db._storage.loadBulk([o._p_oid for o in result])
            elif hasattr(result, "_p_oid"):
                self.db._db._storage.load(result._p_oid)
        return result
