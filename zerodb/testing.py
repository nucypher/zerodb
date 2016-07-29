"""
Pytest fixtures for zerodb tests

To activate the fixtures, add this to your conftest.py:

from zerodb.testing import *
"""
import os
import pytest
import shutil
import tempfile
from time import sleep
from multiprocessing import Process
from os import path

import ZEO.tests.testssl

import zerodb
from zerodb.crypto import ecc, elliptic
from zerodb.util import encode_hex

kdf = elliptic.kdf

TEST_PASSPHRASE = "v3ry 53cr3t pa$$w0rd"
TEST_PUBKEY = ecc.private(
        TEST_PASSPHRASE, ("root", "ZERO"), kdf=kdf).get_pubkey()
TEST_PUBKEY_3 = ecc.private(
        TEST_PASSPHRASE + " third", ("third", "ZERO"), kdf=kdf).get_pubkey()

TEST_PERMISSIONS = """realm ZERO
auth_secp256k1_scrypt:root:%s
auth_secp256k1_scrypt:third:%s""" % (encode_hex(TEST_PUBKEY), encode_hex(TEST_PUBKEY_3))

ZEO_CONFIG = """<zeo>
  address %(sock)s
  authentication-protocol auth_secp256k1_scrypt
  authentication-database %(pass_file)s
  authentication-realm ZERO
</zeo>

<filestorage>
  path %(dbfile)s
  pack-gc false
</filestorage>"""

__all__ = [
    "TEST_PASSPHRASE",
    "TEST_PUBKEY",
    "tempdir",
    "do_zeo_server",
    "db",
]


@pytest.fixture(scope="module")
def tempdir(request):
    tmpdir = tempfile.mkdtemp()
    request.addfinalizer(lambda: shutil.rmtree(tmpdir))
    return tmpdir


@pytest.fixture(scope="module")
def pass_file(request, tempdir):
    filename = path.join(tempdir, "authdb.conf")
    with open(filename, "w") as f:
        f.write(TEST_PERMISSIONS)
    return filename

@pytest.fixture(scope="module")
def db(request, zeo_server, dbclass=zerodb.DB):
    zdb = dbclass(zeo_server,
                  cert_file=ZEO.tests.testssl.client_cert,
                  key_file=ZEO.tests.testssl.client_key,
                  server_cert=ZEO.tests.testssl.server_cert,
                  username='root', key=TEST_PASSPHRASE, debug=True,
                  wait_timeout=11)

    if request is not None:
        @request.addfinalizer
        def fin():
            zdb.disconnect()  # I suppose, it's not really required

    return zdb

def do_zeo_server(request, tempdir, name=None, fsname='db.fs'):
    sock, stop = zerodb.server(name=name, path=os.path.join(tempdir, fsname))
    request.addfinalizer(stop)
    return sock

