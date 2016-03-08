from six import iterkeys
from .query import Eq, Lt, Gt, And, Or, Not, InRange, Contains,\
                  NotEq, Le, Ge, NotInRange, DoesNotContain,\
                  Any, All, NotAny, NotAll

"""
Query examples (similar to http://docs.mongodb.org/manual/reference/operator/query/):

    {"$and": [{"field1": {"$gt": 10}}, {"field2": {"$text": "hello"}}]}
    {field: {"$range": [1, 10]}}
"""

logical_operators = {
        "$and": And,
        "$or": Or,
        "$not": Not}

field_operators = {
        "$eq": Eq,
        "$ne": NotEq,
        "$lt": Lt,
        "$lte": Le,
        "$gt": Gt,
        "$gte": Ge,
        "$range": InRange,
        "$nrange": NotInRange,
        "$text": Contains,
        "$ntext": DoesNotContain,
        "$in": Any,
        "$all": All,
        "$nany": NotAny,
        "$nin": NotAll}


def compile(q):
    """
    :param dict q: deserialized json
    :returns: query object
    :rtype: zerodb.catalog.query.Query
    """
    assert len(q) == 1
    key = next(iterkeys(q))

    if key in logical_operators:
        if isinstance(q[key], list):
            return logical_operators[key](*map(compile, q[key]))
        else:
            return logical_operators[key](compile(q[key]))
    else:
        assert isinstance(q[key], dict)
        assert len(q[key]) == 1
        opkey = next(iterkeys(q[key]))
        params = q[key][opkey]
        if not isinstance(params, list):
            params = [params]
        return field_operators[opkey](key, *params)
