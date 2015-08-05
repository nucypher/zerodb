import pytest
from ZEO.Exceptions import StorageError
from ZODB.DB import z64
from zerodb.permissions import subdb
from zerodb.crypto import ecc
from zerodb.storage import client_storage
from conftest import TEST_PUBKEY, TEST_PASSPHRASE

import logging
logging.basicConfig(level=logging.DEBUG)


def test_db_rootuser(pass_db):
    user = pass_db["root"]
    assert user.administrator
    assert user.pubkey == TEST_PUBKEY


def test_db_users(pass_db):
    pk1 = ecc.private("pass1").get_pubkey()
    pk2 = ecc.private("pass2").get_pubkey()
    pk3 = ecc.private("pass3").get_pubkey()
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


def test_ecc_auth(zeo_server):
    # Presumably, ecc_server already registered auth protocol
    storage = client_storage(zeo_server,
            username="root", password=TEST_PASSPHRASE, realm="ZERO")

    with pytest.raises(StorageError):  # Cannot access common root
        storage.load(z64)

    db = subdb.DB(storage)
    conn = db.open()
    conn.root()

    assert db._root_oid != z64
    assert type(db._root_oid) == str

    conn.close()


def test_user_management(zeo_server):
    storage = client_storage(zeo_server,
            username="root", password=TEST_PASSPHRASE, realm="ZERO")

    pk0 = ecc.private("passY").get_pubkey()
    pk = ecc.private("passX").get_pubkey()
    storage.add_user("userX", pk0)
    storage.change_key("userX", pk)

    storage = client_storage(zeo_server,
            username="userX", password="passX", realm="ZERO")
    with pytest.raises(AssertionError):
        storage.add_user("shouldfail", pk)
