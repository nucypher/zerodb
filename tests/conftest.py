import pytest
import zerodb

from zerodb.testing import *

from db import create_objects_and_close
from db import add_wiki_and_close


@pytest.fixture(scope="module")
def zeo_server(request, tempdir):
    sock = do_zeo_server(request, tempdir, name="zeo_server")
    create_objects_and_close(sock)
    return sock


@pytest.fixture(scope="module")
def wiki_server(request, tempdir):
    """
    :return: Temporary UNIX socket
    :rtype: str
    """
    sock = do_zeo_server(request, tempdir, name="wiki_server")
    add_wiki_and_close(sock)
    return sock


@pytest.fixture(scope="module")
def wiki_db(request, wiki_server):
    return db(request, wiki_server)
