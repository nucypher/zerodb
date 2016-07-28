import pytest
import zerodb
from zerodb.transform.encrypt_aes import AES256Encrypter, AES256EncrypterV0
from zerodb.testing import do_zeo_server, db
from db import Page, create_objects_and_close


class DBAESv0(zerodb.DB):
    encrypter = AES256EncrypterV0


@pytest.fixture(scope="module")
def zeo_server_aes_v0(request, tempdir):
    # Use old pycryptodome encryption
    sock = do_zeo_server(request, tempdir)
    create_objects_and_close(sock, dbclass=DBAESv0)
    return sock


@pytest.fixture(scope="module")
def db_aes_v0(request, zeo_server_aes_v0):
    # Use new zerodb.DB class here
    zdb = db(request, zeo_server_aes_v0)
    return zdb

def test_compat(db_aes_v0):
    # Test whether we can still read the DB
    assert len(db_aes_v0[Page]) > 0
