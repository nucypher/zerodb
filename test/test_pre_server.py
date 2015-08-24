import pytest
from multiprocessing import Process
from os import path
from zerodb.storage import ZEOServer

import zerodb
from db import create_objects_and_close


ZEO_CONFIG = """<zeo>
  address %(sock)s
  authentication-protocol afgh_elliptic_auth
  authentication-database %(pass_file)s
  authentication-realm ZERO
</zeo>

<filestorage>
  path %(dbfile)s
</filestorage>"""


@pytest.fixture(scope="module")
def zeo_server_pre(request, pass_file, tempdir):
    """
    :return: Temporary UNIX socket
    :rtype: str
    """
    from zerodb.permissions import afgh

    class ReDB(zerodb.DB):
        auth_module = afgh

    afgh.register_auth()

    sock = path.join(tempdir, "zeosocket_auth_pre")
    zeroconf_file = path.join(tempdir, "zeo_pre.config")
    dbfile = path.join(tempdir, "db_pre.fs")
    with open(zeroconf_file, "w") as f:
        f.write(ZEO_CONFIG % {
            "sock": sock,
            "pass_file": pass_file,
            "dbfile": dbfile})
    server = Process(target=ZEOServer.run, kwargs={"args": ("-C", zeroconf_file)})

    @request.addfinalizer
    def fin():
        server.terminate()
        server.join()

    server.start()

    create_objects_and_close(sock, count=20, dbclass=ReDB)

    return sock


def test_zeo(zeo_server_pre):
    pass
