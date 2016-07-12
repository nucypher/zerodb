import pytest
import transaction
import six
from ZEO.Exceptions import StorageError
from ZODB.DB import z64
from zerodb.permissions import subdb
from zerodb.crypto import ecc
from zerodb.storage import client_storage
from zerodb.testing import TEST_PASSPHRASE, TEST_PUBKEY, kdf

import logging
logging.basicConfig(level=logging.DEBUG)


# Connections cannot be closed when they are joined to a transaction
@pytest.fixture(scope="function")
def abort(request):
    request.addfinalizer(transaction.abort)


def test_db_rootuser(pass_db):
    user = pass_db["root"]
    assert user.administrator
    assert user.pubkey == TEST_PUBKEY


def test_db_users(pass_db, abort):
    pk1 = ecc.private("pass1", ("user1", "ZERO"), kdf=kdf).get_pubkey()
    pk2 = ecc.private("pass2", ("user2", "ZERO"), kdf=kdf).get_pubkey()
    pk3 = ecc.private("pass3", ("user3", "ZERO"), kdf=kdf).get_pubkey()

    with transaction.manager:
        pass_db.add_user("user1", pk1, administrator=True)
        pass_db.add_user("user2", pk2)
        pass_db.add_user("user3", pk3)
        pass_db.del_user("user3")
        pass_db.change_key("user2", pk3)

    assert pass_db["user1"].administrator
    assert not pass_db["user2"].administrator
    assert pass_db["user1"].pubkey == pk1
    assert pass_db["user2"].pubkey == pk3

    with pytest.raises(LookupError):
        pass_db["user3"]


def test_db_users_abort(pass_db, abort):
    transaction.begin()

    pk4 = ecc.private("pass1", ("user4", "ZERO"), kdf=kdf).get_pubkey()

    pass_db.add_user("user4", pk4)
    pass_db["user4"]

    with pytest.raises(LookupError):
        pass_db.add_user("user4", pk4)

    transaction.abort()

    with pytest.raises(LookupError):
        pass_db["user4"]

    pass_db.add_user("user4", pk4)


def test_ecc_auth(zeo_server):
    # Presumably, ecc_server already registered auth protocol
    storage = client_storage(
            zeo_server, username="root", password=TEST_PASSPHRASE, realm="ZERO")

    with pytest.raises(StorageError):  # Cannot access common root
        storage.load(z64)

    db = subdb.DB(storage)
    conn = db.open()
    conn.root()

    assert db._root_oid != z64
    if six.PY2:
        assert type(db._root_oid) == str
    else:
        assert type(db._root_oid) == bytes

    conn.close()


def test_user_management(zeo_server, abort):
    storage = client_storage(
            zeo_server, username="root", password=TEST_PASSPHRASE, realm="ZERO")

    pk1 = ecc.private("passY", ("userX", "ZERO"), kdf=kdf).get_pubkey()
    pk2 = ecc.private("passX", ("userX", "ZERO"), kdf=kdf).get_pubkey()

    with transaction.manager:
        storage.add_user("userX", pk1)
        storage.change_key("userX", pk2)

    with pytest.raises(LookupError):
        storage.add_user("userX", pk1)

    storage = client_storage(
            zeo_server, username="userX", password="passX", realm="ZERO")

    with pytest.raises(AssertionError):
        storage.add_user("shouldfail", pk1)


def test_user_management_abort(zeo_server, abort):
    storage = client_storage(
            zeo_server, username="root", password=TEST_PASSPHRASE, realm="ZERO")

    pk1 = ecc.private("passY", ("userY", "ZERO"), kdf=kdf).get_pubkey()

    storage.add_user("userY", pk1)

    with pytest.raises(LookupError):
        storage.add_user("userY", pk1)

    transaction.abort()

    # storage.add_user("userY", pk1)  # XXX
