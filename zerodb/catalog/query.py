from zerodbext.catalog import query
from zerodb import trees
from zerodb.util.iter import Sliceable


def _to_set(flavor, data):
    if isinstance(data, Sliceable):
        return flavor.Set(data)
    else:
        return data


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


class Contains(LogicMixin, query.Comparator):
    """Contains query.

    CQE equivalent: 'foo' in index
    """

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyContains(self._get_value(names))

    def __str__(self):
        return '%s in %s' % (repr(self._value), self.index_name)

    def negate(self):
        return DoesNotContain(self.index_name, self._value)


class DoesNotContain(LogicMixin, query.Comparator):
    """CQE equivalent: 'foo' not in index
    """

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyDoesNotContain(self._get_value(names))

    def __str__(self):
        return '%s not in %s' % (repr(self._value), self.index_name)

    def negate(self):
        return Contains(self.index_name, self._value)


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
        return index.applyGt(self._get_value(names))

    def negate(self):
        return Le(self.index_name, self._value)


class Lt(Comparator):
    """ Less than query.

    CQE equivalent: index < 'foo'
    """
    operator = '<'

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyLt(self._get_value(names))

    def negate(self):
        return Ge(self.index_name, self._value)


class Ge(Comparator):
    """Greater (or equal) query.

    CQE equivalent: index >= 'foo'
    """
    operator = '>='

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyGe(self._get_value(names))

    def negate(self):
        return Lt(self.index_name, self._value)


class Le(Comparator):
    """Less (or equal) query.

    CQE equivalent: index <= 'foo
    """
    operator = '<='

    def _apply(self, catalog, names):
        index = self._get_index(catalog)
        return index.applyLe(self._get_value(names))

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
            self.start_exclusive, self.end_exclusive)

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
            self.start_exclusive, self.end_exclusive)

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

    def _apply(self, catalog, names):
        # XXX Or query can be done lazily using heapq's sorted join
        IF = self.family.IF
        queries = self.queries
        result = queries[0]._apply(catalog, names)
        for q in queries[1:]:
            next_result = q._apply(catalog, names)
            if len(result) == 0:
                result = next_result
            elif len(next_result) > 0:
                _, result = self.family.IF.weightedUnion(_to_set(IF, result), _to_set(IF, next_result))
        return result


class And(LogicMixin, query.And):
    family = trees.family32

    def _apply(self, catalog, names):
        # XXX figure out doing smallest part first for performance
        IF = self.family.IF
        queries = self.queries
        result = queries[0]._apply(catalog, names)
        for q in queries[1:]:
            if len(result) == 0:
                return IF.Set()
            next_result = q._apply(catalog, names)
            if len(next_result) == 0:
                return IF.Set()
            _, result = IF.weightedIntersection(_to_set(IF, result), _to_set(IF, next_result))
        return result


class Not(LogicMixin, query.Not):
    pass


class Name(LogicMixin, query.Name):
    pass

optimize = query.optimize
parse_query = query.parse_query
