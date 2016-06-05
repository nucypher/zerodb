import pytest
from pickle import loads
from zerodb.storage import client_storage
from zerodb.testing import TEST_PASSPHRASE


@pytest.fixture(scope="module")
def zeo_storage(request, zeo_server):
    return client_storage(zeo_server,
            username="root", password=TEST_PASSPHRASE, realm="ZERO", debug=True)


def test_loadBulk(zeo_storage):
    # oids in ZODB start from zero, and there are less than 10
    root_id, _ = zeo_storage.get_root_id()
    count_0 = zeo_storage._debug_download_count
    oids = [root_id]
    out = zeo_storage.loadBulk(oids)
    count_1 = zeo_storage._debug_download_count
    assert count_1 - count_0 == 1

    assert len(out) == len(oids)

    for dump, oid in out:
        assert loads(dump) is not None

    for oid in oids:
        assert zeo_storage._cache.load(oid)

    for oit in oids:
        zeo_storage.load(oid)
    assert zeo_storage._debug_download_count == count_1
