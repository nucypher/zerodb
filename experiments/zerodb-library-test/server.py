#!/usr/bin/python
import sys

from os.path import abspath, dirname, join
parent = dirname(dirname(dirname(abspath(__file__))))
sys.path.insert(0, parent)

from zerodb.storage import ZEOServer

import logging
logging.basicConfig(level=logging.DEBUG)

SOCKET = "/tmp/zeosocket"

if __name__ == "__main__":
    dbfile = join(dirname(abspath(__file__)), "db", "test.fs")
    server = ZEOServer.run(args=("-a", SOCKET, "-f", dbfile))
