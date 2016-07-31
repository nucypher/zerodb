"""
Pytest fixtures for zerodb tests

To activate the fixtures, add this to your conftest.py:

from zerodb.testing import *
"""
import os
import pytest
import shutil
import tempfile

import ZEO.tests.testssl

import zerodb
from zerodb.crypto import kdf

TEST_PASSPHRASE = "v3ry 53cr3t pa$$w0rd"


__all__ = [
    "TEST_PASSPHRASE",
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
def db(request, zeo_server, dbclass=zerodb.DB):
    zdb = dbclass(zeo_server,
                  username='root', password=TEST_PASSPHRASE,
                  security=kdf.key_from_password,
                  server_cert=ZEO.tests.testssl.server_cert,
                  debug=True, wait_timeout=11)

    if request is not None:
        @request.addfinalizer
        def fin():
            zdb.disconnect()  # I suppose, it's not really required

    return zdb


def do_zeo_server(request, tempdir, name=None, fsname='db.fs'):
    sock, stop = zerodb.server(
            name=name, path=os.path.join(tempdir, fsname),
            init=dict(
                password=TEST_PASSPHRASE, cert=ZEO.tests.testssl.client_cert
                ))
    request.addfinalizer(stop)
    return sock
