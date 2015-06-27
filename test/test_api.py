import pytest
import logging
import requests
import socket
import time
from json import loads
from multiprocessing import Process
from os import path
from db import TEST_PASSPHRASE
from zerodb import api


logging.basicConfig(level=logging.DEBUG)


def api_run(**kw):
    api.run(use_reloader=False, **kw)


@pytest.fixture(scope="module")
def api_server(request, db):
    # Get available TCP port
    sock = socket.socket()
    sock.bind(("localhost", 0))
    _, port = sock.getsockname()
    sock.close()

    server = Process(target=api_run, kwargs={
        "host": "localhost",
        "port": port,
        "data_models": path.join(path.dirname(__file__), "db.py")})

    @request.addfinalizer
    def fin():
        server.terminate()
        server.join()

    server.start()
    time.sleep(0.2)

    return {
            "api_uri": "http://localhost:%s" % port,
            "zeo_uri": db._storage._addr}


def test_connect(api_server):
    session = requests.Session()

    # Connect
    resp = session.get(api_server["api_uri"] + "/_connect", params={
        "username": "root",
        "passphrase": TEST_PASSPHRASE,
        "host": api_server["zeo_uri"]})
    assert loads(resp.text)["ok"] == 1

    # Disconnect
    resp = session.get(api_server["api_uri"] + "/_disconnect")
    assert loads(resp.text)["ok"] == 1
