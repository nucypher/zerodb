import pytest
from os import path
from zerodb.storage import batch
from multiprocessing import Process
import db


@pytest.fixture(scope="module")
def zeo_server(request, tempdir):
    """ Returns a temporary UNIX socket """
    sock = path.join(tempdir, "zeosocket")
    dbfile = path.join(tempdir, "testdb.fs")
    server = Process(target=batch.zeoserver_main, kwargs={"args": ("-a", sock, "-f", dbfile)})

    @request.addfinalizer
    def fin():
        server.terminate()
        server.join()

    server.start()

    db.create_objects_and_close(sock)

    return sock


@pytest.fixture(scope="module")
def zeo_client(request, zeo_server):
    root = db.get_zodb(zeo_server)
    return root


def test_client(zeo_client):
    assert len(zeo_client['pages']) == 200
