from repoze.catalog import query
from repoze.catalog.indexes import field
from zerodb import trees


def _prefetch(catalog, index):
    """This method should be removed once all the fields have prefetch argument"""
    kw = {}
    if isinstance(index, field.CatalogFieldIndex):
        kw["prefetch"] = catalog
    return kw


class LogicMixin:
    def __and__(self, right):
        self._check_type("and", right)
        return And(self, right)

    def __or__(self, right):
        self._check_type("or", right)
        return Or(self, right)


class Query(LogicMixin, query.Query):
    pass


class Comparator(LogicMixin, query.Comparator):
    pass


class Contains(LogicMixin, query.Contains):
    pass


class DoesNotContain(LogicMixin, query.DoesNotContain):
    pass


class Eq(LogicMixin, query.Eq):
    pass


class NotEq(LogicMixin, query.NotEq):
    pass


class Gt(Comparator):
    """ Greater than query.

    CQE equivalent: index > 'foo'
    """
    operator = '>'

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyGt(self._get_value(names), **_prefetch(catalog, index))

    def negate(self):
        return Le(self.index_name, self._value)


class Lt(Comparator):
    """ Less than query.

    CQE equivalent: index < 'foo'
    """
    operator = '<'

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyLt(self._get_value(names), **_prefetch(catalog, index))

    def negate(self):
        return Ge(self.index_name, self._value)


class Ge(Comparator):
    """Greater (or equal) query.

    CQE equivalent: index >= 'foo'
    """
    operator = '>='

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyGe(self._get_value(names), **_prefetch(catalog, index))

    def negate(self):
        return Lt(self.index_name, self._value)


class Le(Comparator):
    """Less (or equal) query.

    CQE equivalent: index <= 'foo
    """
    operator = '<='

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyLe(self._get_value(names), **_prefetch(catalog, index))

    def negate(self):
        return Gt(self.index_name, self._value)


class InRange(LogicMixin, query.InRange):
    """ Index value falls within a range.

    CQE eqivalent: lower < index < upper
                   lower <= index <= upper
    """

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyInRange(
            self._get_start(names), self._get_end(names),
            self.start_exclusive, self.end_exclusive, **_prefetch(catalog, index))

    def negate(self):
        return NotInRange(self.index_name, self._start, self._end,
                          self.start_exclusive, self.end_exclusive)


class NotInRange(LogicMixin, query.NotInRange):
    """ Index value falls outside a range.

    CQE eqivalent: not(lower < index < upper)
                   not(lower <= index <= upper)
    """

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyNotInRange(
            self._get_start(names), self._get_end(names),
            self.start_exclusive, self.end_exclusive, **_prefetch(catalog, index))

    def negate(self):
        return InRange(self.index_name, self._start, self._end,
                       self.start_exclusive, self.end_exclusive)


class Any(LogicMixin, query.Any):
    pass


class NotAny(LogicMixin, query.NotAny):
    pass


class All(LogicMixin, query.All):
    pass


class NotAll(LogicMixin, query.NotAll):
    pass


class BoolOp(LogicMixin, query.BoolOp):
    family = trees.family32


class Or(LogicMixin, query.Or):
    family = trees.family32


class And(LogicMixin, query.And):
    family = trees.family32


class Not(LogicMixin, query.Not):
    pass


class Name(LogicMixin, query.Name):
    pass

optimize = query.optimize
parse_query = query.parse_query
