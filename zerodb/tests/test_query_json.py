from six import StringIO
from zerodb.catalog import query_json as qj
from zerodb.catalog.query import optimize
from zerodb.catalog.query import Gt, Contains
from zerodb.catalog.query import Not, Eq, InRange


def qtree(q):
    q = optimize(q)
    f = StringIO()
    q.print_tree(out=f)
    f.seek(0)
    out = f.read()
    f.close()
    return out


def test_query_json():
    q1 = qj.compile({"$and": [{"field1": {"$gt": 10}}, {"field2": {"$eq": "hello"}}]})
    q2 = Gt("field1", 10) & Eq("field2", "hello")
    assert qtree(q1) == qtree(q2)

    q1 = qj.compile({"$not": {"$or": [{"field1": {"$range": [1, 15]}}, {"field2": {"$text": "hello"}}]}})
    q2 = Not(InRange("field1", 1, 15) | Contains("field2", "hello"))
    assert qtree(q1) == qtree(q2)
