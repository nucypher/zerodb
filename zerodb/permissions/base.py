import ssl

from BTrees.OOBTree import BTree, TreeSet
from ZODB.utils import z64
import persistent
import persistent.mapping
import ZODB
import ZODB.FileStorage

from . import subdb

class User(persistent.Persistent):

    def __init__(self, id, username, root):
        """
        :param str od: User id
        :param str username: User name
        :param PersistentMapping: User's database root
        """
        self.id = id
        self.username = username
        self.root = root
        self.certs = {} # {cert_der -> cert_pem}

def init_db(db, uname, pem_data):

    user = User(z64, uname, persistent.mapping.PersistentMapping())
    context = ssl.create_default_context(cadata=pem_data)
    [cert_der] = context.get_ca_certs(1)
    user.certs[cert_der] = pem_data

    with db.transaction() as conn:
        conn.root.users        = BTree()   # {uid -> user}
        conn.root.users_by_der = BTree()   # {cert_der -> user}
        conn.root.admins       = TreeSet() # {admin_user_id}

        conn.root.users[user.id] = conn.root.users_by_der[cert_der] = user
        conn.root.admins.add(user.id)
        conn.root.certs = pem_data

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
