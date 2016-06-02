import pytest
import shutil
import tempfile
from time import sleep
from multiprocessing import Process
from os import path

import zerodb
from zerodb.crypto import ecc
from zerodb.permissions import elliptic
from zerodb.permissions import base as permissions_base
from zerodb.storage import ZEOServer
from zerodb.util import encode_hex

from db import TEST_PASSPHRASE
from db import create_objects_and_close, add_wiki_and_close

TEST_PUBKEY = ecc.private(TEST_PASSPHRASE).get_pubkey()
TEST_PUBKEY_3 = ecc.private(TEST_PASSPHRASE + " third").get_pubkey()
TEST_PERMISSIONS = """realm ZERO
root:%s
third:%s""" % (encode_hex(TEST_PUBKEY), encode_hex(TEST_PUBKEY_3))

ZEO_CONFIG = """<zeo>
  address %(sock)s
  authentication-protocol ecc_auth
  authentication-database %(pass_file)s
  authentication-realm ZERO
</zeo>

<filestorage>
  path %(dbfile)s
  pack-gc false
</filestorage>"""

elliptic.register_auth()


@pytest.fixture(scope="module")
def pass_file(request, tempdir):
    filename = path.join(tempdir, "authdb.conf")
    with open(filename, "w") as f:
        f.write(TEST_PERMISSIONS)
    return filename


@pytest.fixture(scope="function")
def pass_db(request, pass_file):
    pdb = permissions_base.PermissionsDatabase(pass_file)
    request.addfinalizer(pdb.close)
    return pdb


def do_zeo_server(request, pass_file, tempdir):
    """
    :return: Temporary UNIX socket
    :rtype: str
    """
    sock = path.join(tempdir, "zeosocket_auth")
    zeroconf_file = path.join(tempdir, "zeo.config")
    dbfile = path.join(tempdir, "db2.fs")
    with open(zeroconf_file, "w") as f:
        f.write(ZEO_CONFIG % {
            "sock": sock,
            "pass_file": pass_file,
            "dbfile": dbfile})
    server = Process(target=ZEOServer.run, kwargs={"args": ("-C", zeroconf_file)})

    @request.addfinalizer
    def fin():
        sleep(1)
        server.terminate()
        server.join(1)

    server.daemon = True
    server.start()

    return sock


@pytest.fixture(scope="module")
def zeo_server(request, pass_file, tempdir):
    sock = do_zeo_server(request, pass_file, tempdir)
    create_objects_and_close(sock)
    return sock


@pytest.fixture(scope="module")
def tempdir(request):
    tmpdir = tempfile.mkdtemp()
    request.addfinalizer(lambda: shutil.rmtree(tmpdir))
    return tmpdir


@pytest.fixture(scope="module")
def db(request, zeo_server):
    zdb = zerodb.DB(zeo_server, username="root", password=TEST_PASSPHRASE, debug=True)

    @request.addfinalizer
    def fin():
        zdb.disconnect()  # I suppose, it's not really required

    return zdb


@pytest.fixture(scope="module")
def wiki_server(request, pass_file, tempdir):
    """
    :return: Temporary UNIX socket
    :rtype: str
    """
    sock = do_zeo_server(request, pass_file, tempdir)
    add_wiki_and_close(sock)
    return sock


@pytest.fixture(scope="module")
def wiki_db(request, wiki_server):
    zdb = zerodb.DB(wiki_server, username="root", password=TEST_PASSPHRASE, debug=True)

    @request.addfinalizer
    def fin():
        zdb.disconnect()  # I suppose, it's not really required

    return zdb
