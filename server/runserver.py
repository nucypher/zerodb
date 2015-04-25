#!/usr/bin/env python2

"""
Simple script to run db server.
You can specify db path and socket name (can be UNIX or TCP socket).
"""

import click
import tempfile
import os
from os import path

from zerodb.storage import ZEOServer

TEMP_DIR = tempfile.gettempdir()
TEMP_SOCK = path.join(TEMP_DIR, "zerosocket")
DEFAULT_DB_PATH = path.join(path.dirname(__file__), "db", "db.fs")


@click.command()
@click.option("--socket", default=TEMP_SOCK, help="Socket to connect to")
@click.option("--dbpath", default=DEFAULT_DB_PATH, help="File to store db")
def run(socket, dbpath):
    dbdir = path.dirname(dbpath)
    if not path.exists(dbdir):
        os.mkdir(dbdir)
    if path.exists(socket):
        os.remove(socket)  # XXX need to check if it's unix socket and if it's busy
    ZEOServer.run(["-a", socket, "-f", dbpath])


if __name__ == "__main__":
    run()
