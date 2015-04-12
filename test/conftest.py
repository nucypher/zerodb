import pytest
import shutil
import tempfile
from multiprocessing import Process
from os import path
from zerodb.storage import ZEOServer
import dbm as db


@pytest.fixture(scope="module")
def tempdir(request):
    tmpdir = tempfile.mkdtemp()
    request.addfinalizer(lambda: shutil.rmtree(tmpdir))
    return tmpdir


@pytest.fixture(scope="module")
def zeo_server(request, tempdir):
    """ Returns a temporary UNIX socket """
    sock = path.join(tempdir, "zeosocket")
    dbfile = path.join(tempdir, "testdb.fs")
    server = Process(target=ZEOServer.run, kwargs={"args": ("-a", sock, "-f", dbfile)})

    @request.addfinalizer
    def fin():
        server.terminate()
        server.join()

    server.start()

    db.create_objects_and_close(sock)

    return sock
