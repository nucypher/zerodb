import pytest
import zerodb
from dbm import Page, Salary
from repoze.catalog.query import Contains, InRange
# Also need to test optimize, Lt(e), Gt(e)


@pytest.fixture(scope="module")
def db(request, zeo_server):
    zdb = zerodb.DB(zeo_server, debug=True)

    @request.addfinalizer
    def fin():
        zdb.disconnect()  # I suppose, it's not really required

    return zdb


def test_query(db):
    assert len(db[Page]) == 200
    assert len(db[Salary]) == 200
    test_pages = db[Page].query(Contains("text", "something"), sort_index="title", limit=2)
    test_salaries_1 = db[Salary].query(InRange("salary", 130000, 180000), sort_index="salary", limit=2)
    test_salaries_2 = db[Salary].query(InRange("salary", 130000, 130001), sort_index="salary", limit=2)
    assert len(test_pages) == 2
    assert len(test_salaries_1) == 2
    assert len(test_salaries_2) == 0
    for s in test_salaries_1:
        assert s.salary >= 130000
        assert s.salary <= 180000
