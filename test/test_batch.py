import pytest
from pickle import loads
import db


@pytest.fixture(scope="module")
def zeo_storage(request, zeo_server):
    return db.get_storage(zeo_server)


def test_loadBulk(zeo_storage):
    # oids in ZODB start from zero, and there are less than 10
    oids = [("000000000000000%s" % i).decode('hex') for i in range(10)]
    out = zeo_storage.loadBulk(oids)

    assert len(out) == len(oids)

    for dump, oid in out:
        assert loads(dump) is not None

    for oid in oids:
        assert zeo_storage._cache.load(oid)
