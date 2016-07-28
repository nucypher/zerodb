"""User database management

The concept of"root" is a little tricky, so we try to avoid using it
for admin purposes.  For this reason, we add an Admin object ro the
root and assure that it has oid 1, allowing us to navigate to it
without going through the root.

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
from ZODB.utils import z64, p64
import hashlib
import persistent
import persistent.mapping
import ZODB
import ZODB.FileStorage

from zerodb.crypto import elliptic
from zerodb.crypto import cert
from .ownerstorage import OwnerStorage

kdf = elliptic.kdf  # TODO This should be configurable
ONE = p64(1)

def get_der(pem_data):
    context = ssl.create_default_context(cadata=pem_data)
    [cert_der] = context.get_ca_certs(1) # TCBOO
    return cert_der

class User(persistent.Persistent):

    def __init__(self, name, root):
        """
        :param str od: User id
        :param str name: User name
        :param PersistentMapping: User's database root
        """
        self.name = name
        self.root = root
        self.id = root._p_oid
        # Today, TCBOO cert, but maybe later
        self.certs = {} # {cert_der -> cert_pem}

class Certs(persistent.Persistent):

    def __init__(self):
        self.data = ''

    def add(self, pem_data):
        self.data += '\n\n' + pem_data

    def remove(self, pem_data):
        self.data = self.data.replace('\n\n' + pem_data, '')

class Admin(persistent.Persistent):

    def __init__(self, conn):
        conn.add(self)
        assert self._p_oid == ONE

        self.users         = BTree() # {uid -> user}
        self.users_by_name = BTree() # {uname -> user}
        self.uids          = BTree() # {cert_der -> uid}
        self.certs         = Certs() # Cert, persistent wrapper for
                                     # concatinated cert data

    def add_user(self, uname, password=None, pem_data=None):
        root = persistent.mapping.PersistentMapping()
        self._p_jar.add(root)

        user = User(uname, root)
        self.users[user.id] = user
        self.users_by_name[user.name] = user

        if pem_data:
            self._add_user_cert(user, pem_data)
        elif password:
            self._add_user_password(user, password)
        else:
            raise AttributeError("You should specify pem_data or password")

        return user

    def _add_user_cert(self, user, pem_data):
        cert_der = get_der(pem_data)
        if cert_der in self.uids or cert_der in user.certs:
            raise ValueError("SSL certificate id already used",
                             pem_data, user.id)
        self.uids[cert_der] = user.id
        user.certs[cert_der] = pem_data
        self.certs.add(pem_data)

    def _add_user_password(self, user, password):
        salt = user.name + "|ZERO"
        aes_key = kdf(password, salt)
        ssl_key = hashlib.sha256(aes_key).digest()
        _, pub_pem = cert.pkey2cert(ssl_key)
        self._add_user_cert(user, pub_pem)

    def _del_user_certs(self, user):
        for der, pem_data in user.certs.items():
            del self.uids[der]
            self.certs.remove(pem_data)

    def del_user(self, name):
        user = self.users_by_name.pop(name)
        del self.users[user.id]
        self._del_user_certs(user)

    def change_cert(self, name, pem_data):
        user = self.users_by_name[name]
        self._del_user_certs(user)
        user.certs.clear()

        self._add_user_cert(user, pem_data)

    def change_password(self, name, password):
        user = self.users_by_name[name]
        self._del_user_certs(user)
        user.certs.clear()

        self._add_user_password(user, password)


def get_admin(conn):
    return conn.get(ONE)

def init_db(storage, uname, pem_data, close=True):
    db = ZODB.DB(OwnerStorage(storage, p64(2)))
    with db.transaction() as conn:
        conn.root.admin = Admin(conn)
        user = conn.root.admin.add_user(uname, pem_data=pem_data)
        assert user.id == db.storage.user_id
    if close:
        db.close()

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

    with open(options.certificate) as f:
        pem_data = f.read()

    init_db(ZODB.FileStorage.FileStorage(path), options.user, pem_data)
