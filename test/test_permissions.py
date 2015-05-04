import pytest
from os import path
from multiprocessing import Process
from ZODB.DB import z64
from zerodb.permissions.sign import\
        PermissionsDatabase,\
        ecc,\
        AccessDeniedError,\
        register_auth
from zerodb.storage import ZEOServer
from zerodb.crypto import AES
from zerodb.storage import client_storage
from zerodb.permissions.sign import DB

import logging
logging.basicConfig(level=logging.DEBUG)

TEST_PASSPHRASE = "v3ry 53cr3t pa$$w0rd"
TEST_PUBKEY = ecc.private(TEST_PASSPHRASE).get_pubkey()
TEST_PERMISSIONS = """realm ZERO
root:%s""" % TEST_PUBKEY.encode("hex")

ZEO_CONFIG = """<zeo>
  address %(sock)s
  authentication-protocol ecc_auth
  authentication-database %(pass_file)s
  authentication-realm ZERO
</zeo>

<filestorage>
  path %(dbfile)s
</filestorage>"""


@pytest.fixture(scope="module")
def pass_file(request, tempdir):
    filename = path.join(tempdir, "authdb.conf")
    with open(filename, "w") as f:
        f.write(TEST_PERMISSIONS)
    return filename


@pytest.fixture(scope="function")
def pass_db(request, pass_file):
    db = PermissionsDatabase(pass_file)
    request.addfinalizer(db.close)
    return db


@pytest.fixture(scope="function")
def ecc_server(request, pass_file, tempdir):
    sock = path.join(tempdir, "zeosocket_auth")
    zeroconf_file = path.join(tempdir, "zeo.config")
    dbfile = path.join(tempdir, "db2.fs")
    with open(zeroconf_file, "w") as f:
        f.write(ZEO_CONFIG % {
            "sock": sock,
            "pass_file": pass_file,
            "dbfile": dbfile})
    register_auth()
    server = Process(target=ZEOServer.run, kwargs={"args": ("-C", zeroconf_file)})

    @request.addfinalizer
    def fin():
        server.terminate()
        server.join()

    server.start()
    return sock


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


def test_ecc_auth(ecc_server):
    # Presumably, ecc_server already registered auth protocol
    storage = client_storage(ecc_server,
            username="root", password=TEST_PASSPHRASE, realm="ZERO",
            cipher=AES(passphrase=TEST_PASSPHRASE))
    with pytest.raises(AccessDeniedError):
        storage.load(z64)
    db = DB(storage)
    conn = db.open()
    conn.root  # Do we save data??
    conn.close()
    # Now should create a DB and test private root from connection
