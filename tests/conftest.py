import pytest
import zerodb

from zerodb.testing import *

from db import create_objects_and_close
from db import add_wiki_and_close


@pytest.fixture(scope="module")
def zeo_server(request, pass_file, tempdir):
    sock = do_zeo_server(request, pass_file, tempdir, name="zeo_server")
    create_objects_and_close(sock)
    return sock


# @pytest.fixture(scope="module")
# def db(request, zeo_server):
#     zdb = zerodb.DB(zeo_server, username="root", password=TEST_PASSPHRASE, debug=True)
#
#     @request.addfinalizer
#     def fin():
#         zdb.disconnect()  # I suppose, it's not really required
#
#     return zdb


@pytest.fixture(scope="module")
def wiki_server(request, pass_file, tempdir):
    """
    :return: Temporary UNIX socket
    :rtype: str
    """
    sock = do_zeo_server(request, pass_file, tempdir, name="wiki_server")
    add_wiki_and_close(sock)
    return sock


@pytest.fixture(scope="module")
def wiki_db(request, wiki_server):
    zdb = zerodb.DB(wiki_server, username="root", password=TEST_PASSPHRASE, debug=True)

    @request.addfinalizer
    def fin():
        zdb.disconnect()  # I suppose, it's not really required

    return zdb
