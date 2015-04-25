import pytest
from pickle import loads
from zerodb.crypto import AES
from zerodb.storage import client_storage
from db import PASSPHRASE


@pytest.fixture(scope="module")
def zeo_storage(request, zeo_server):
    return client_storage(zeo_server, cipher=AES(passphrase=PASSPHRASE), debug=True)


def test_loadBulk(zeo_storage):
    # oids in ZODB start from zero, and there are less than 10
    count_0 = zeo_storage._debug_download_count
    oids = [("000000000000000%s" % i).decode('hex') for i in range(10)]
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
