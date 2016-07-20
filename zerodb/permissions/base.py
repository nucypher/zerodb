"""User database management

Database root objects::

  users: {userid -> User}
  users_by_der: {der -> User}
  certs: Certs

Where DER is a DER encoding of a cert.

The root user's user id is z64 (aka 0).

All other user's ids are the oids of their root folders.

Users have certs: {der -> pem_data}

The Certs object is just a persistent container for the concatenation
of all of the user certs.

"""

import ssl

from BTrees.OOBTree import BTree
from ZODB.utils import z64
import persistent
import persistent.mapping
import ZODB
import ZODB.FileStorage

from . import subdb

class User(persistent.Persistent):

    def __init__(self, username, root):
        """
        :param str od: User id
        :param str username: User name
        :param PersistentMapping: User's database root
        """
        self.username = username
        self.root = root
        self.id = root._p_oid
        self.certs = {} # {cert_der -> cert_pem}

class Certs(persistent.Persistent):

    def __init__(self):
        self.data = ''

    def add(self, pem_data):
        self.data += '\n\n' + pem_data

def get_der(pem_data):
    context = ssl.create_default_context(cadata=pem_data)
    [cert_der] = context.get_ca_certs(1) # TCBOO
    return cert_der

def add_user(conn, uname, pem_data, user_id=None):
    root = persistent.mapping.PersistentMapping()
    conn.add(root)

    user = User(uname, root)
    if user_id:
        if user_id in conn.root.users:
            raise ValueError("User id already used", user_id)
        user.id = user_id # root user is special

    conn.root.users[user.id] = user

    cert_der = get_der(pem_data)
    if cert_der in conn.root.users_by_der or cert_der in user.certs:
        raise ValueError("SSL certificate id already used",
                         pem_data, user.id)
    conn.root.users_by_der[cert_der] = user
    user.certs[cert_der] = pem_data
    conn.root.certs.add(pem_data)

def init_db(db, uname, pem_data):
    with db.transaction() as conn:
        conn.root.users        = BTree()   # {uid -> user}
        conn.root.users_by_der = BTree()   # {cert_der -> user}
        conn.root.certs =        Certs()   # {cert_der -> user}

        add_user(conn, uname, pem_data, z64)

def init_db_script():
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Create an initialized ZeroDB file-storage with a root user"
        )
    parser.add_argument("path", help="Path for new file-storage file")
    parser.add_argument("user", help="Name of root user")
    parser.add_argument("certificate", help="Path to user certificate")

    options = parser.parse_args()

    path = options.path
    if os.path.exists(path):
        raise ValueError("Path exists", path)

    db = ZODB.DB(subdb.OwnerStorage(ZODB.FileStorage.FileStorage(path), z64))

    with open(options.certificate) as f:
        pem_data = f.read()

    init_db(db, options.user, pem_data)
    db.close()
