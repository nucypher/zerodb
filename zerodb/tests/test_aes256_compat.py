import pytest
import zerodb
from zerodb.transform.encrypt_aes import AES256Encrypter, AES256EncrypterV0
from conftest import do_zeo_server
from db import Page, TEST_PASSPHRASE, create_objects_and_close


class DBAESv0(zerodb.DB):
    encrypter = AES256EncrypterV0


@pytest.fixture(scope="module")
def zeo_server_aes_v0(request, pass_file, tempdir):
    # Use old pycryptodome encryption
    sock = do_zeo_server(request, pass_file, tempdir, dbclass=DBAESv0)
    create_objects_and_close(sock)
    return sock


@pytest.fixture(scope="module")
def db_aes_v0(request, zeo_server):
    # Use new zerodb.DB class here
    zdb = zerodb.DB(zeo_server, username="root", password=TEST_PASSPHRASE, debug=True)

    @request.addfinalizer
    def fin():
        zdb.disconnect()

    return zdb


def test_compat(db_aes_v0):
    # Test whether we can still read the DB
    assert len(db_aes_v0[Page]) > 0
