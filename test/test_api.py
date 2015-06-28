import pytest
import logging
import requests
import socket
import time
from json import loads, dumps
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


def api_connect(api_server, session):
    return session.get(api_server["api_uri"] + "/_connect", params={
        "username": "root",
        "passphrase": TEST_PASSPHRASE,
        "host": api_server["zeo_uri"]})


def api_disconnect(api_server, session):
    return session.get(api_server["api_uri"] + "/_disconnect")


def test_connect(api_server):
    session = requests.Session()

    # Connect
    resp = api_connect(api_server, session)
    assert loads(resp.text)["ok"] == 1

    # Disconnect
    resp = api_disconnect(api_server, session)
    assert loads(resp.text)["ok"] == 1


def test_insert_get(api_server):
    session = requests.Session()
    docs = [{"title": "test inserting one", "text": "Here we go, test insert"},
            {"title": "test inserting two", "text": "What's going on here?"}]

    api_connect(api_server, session)

    resp = session.post(api_server["api_uri"] + "/Page/_insert",
            data={"docs": dumps(docs)})
    resp = loads(resp.text)

    assert resp["status"]["ok"] == 1
    oids = [o["$oid"] for o in resp["oids"]]
    assert all(oids)

    resp = session.post(api_server["api_uri"] + "/Page/_get", data={"_id": dumps(oids)})
    resp = loads(resp.text)
    assert resp == docs

    api_disconnect(api_server, session)


def test_find(api_server):
    session = requests.Session()
    api_connect(api_server, session)

    resp = session.post(api_server["api_uri"] + "/Page/_find", data={
        "criteria": dumps({"text": {"$text": "something"}})
        })
    resp = loads(resp.text)
    assert len(resp) == 10

    resp = session.post(api_server["api_uri"] + "/Salary/_find", data={
        "criteria": dumps({"salary": {"$range": [130000, 180000]}}),
        "limit": 2,
        "sort": "salary"
        })
    resp = loads(resp.text)
    assert len(resp) == 2

    resp = session.post(api_server["api_uri"] + "/Salary/_find", data={
        "criteria": dumps({"salary": {"$range": [130000, 130001]}}),
        "limit": 2,
        "sort": {"salary": -1}
        })
    resp = loads(resp.text)
    assert len(resp) == 0

    api_disconnect(api_server, session)
