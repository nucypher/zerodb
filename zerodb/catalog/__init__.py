from zerodbext.catalog.catalog import ResultSetSize
from zerodbext.catalog.catalog import Catalog as _Catalog
from zerodb import trees


class Catalog(_Catalog):
    family = trees.family32

    def sort_result(self, result, sort_index=None, limit=None, sort_type=None,
                    reverse=False):

        if sort_index:
            result = set(result)
            numdocs = total = len(result)
            index = self[sort_index]
            result = index.sort(result, reverse=reverse, limit=limit,
                                sort_type=sort_type)
            if limit:
                numdocs = min(numdocs, limit)
            size = ResultSetSize(numdocs, total)
        else:
            if limit:
                size = ResultSetSize(limit, None)
            else:
                size = None

        return size, result
