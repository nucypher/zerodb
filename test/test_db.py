import pytest
import zerodb
from zerodb.crypto import AES
from db import Page, Salary, PASSPHRASE
from zerodb.catalog.query import Contains, InRange
# Also need to test optimize, Lt(e), Gt(e)


@pytest.fixture(scope="module")
def db(request, zeo_server):
    zdb = zerodb.DB(zeo_server, cipher=AES(passphrase=PASSPHRASE), debug=True)

    @request.addfinalizer
    def fin():
        zdb.disconnect()  # I suppose, it's not really required

    return zdb


def test_query(db):
    pre_request_count = db._storage._debug_download_count
    assert len(db[Page]) == 200
    assert len(db[Salary]) == 200
    test_pages = db[Page].query(Contains("text", "something"))
    pre_range_count = db._storage._debug_download_count
    assert pre_range_count - pre_request_count < 20  # We'll have performance testing separately this way
    test_salaries_1 = db[Salary].query(InRange("salary", 130000, 180000), sort_index="salary", limit=2)
    test_salaries_2 = db[Salary].query(InRange("salary", 130000, 130001), sort_index="salary", limit=2)
    post_range_count = db._storage._debug_download_count
    assert len(test_pages) == 10
    assert len(test_salaries_1) == 2
    assert len(test_salaries_2) == 0
    for s in test_salaries_1:
        assert s.salary >= 130000
        assert s.salary <= 180000
    # Check that we pre-downloaded all objects into cache
    assert db._storage._debug_download_count == post_range_count
