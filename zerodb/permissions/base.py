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
import hashlib
import os
import ssl
import uuid

from BTrees.OOBTree import BTree
from ZODB.utils import p64
import persistent
import persistent.mapping
import ZODB
import ZODB.FileStorage

from zerodb.crypto import kdf

from .ownerstorage import OwnerStorage

ONE = p64(1)


def get_der(pem_data):
    context = ssl.create_default_context(cadata=pem_data)
    [cert_der] = context.get_ca_certs(1)  # TCBOO
    return cert_der


def hash_password(password, salt):
    if not isinstance(password, bytes):
        password = password.encode()
    if not isinstance(salt, bytes):
        salt = salt.encode()
    return b'sha256::' + hashlib.sha256(password + salt).digest()


class User(persistent.Persistent):

    password = None

    def __init__(self, name, root, password=None):
        """
        :param str od: User id
        :param str name: User name
        :param PersistentMapping: User's database root
        """
        self.name = name
        self.root = root
        self.id = root._p_oid
        # Today, TCBOO cert, but maybe later
        self.certs = {}  # {cert_der -> cert_pem}

        if password:
            self.salt = uuid.uuid4().hex.encode()
            self.password = hash_password(password, self.salt)

    def check_password(self, password):
        return hash_password(password, self.salt) == self.password

    def change_password(self, password):
        if password is not None:
            if password:
                self.password = hash_password(password, self.salt)
            else:
                self.password = None


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

        self.users         = BTree()  # {uid -> user}
        self.users_by_name = BTree()  # {uname -> user}
        self.uids          = BTree()  # {cert_der -> uid}
        self.certs         = Certs()  # Cert, persistent wrapper for
                                      # concatinated cert data

        # Add nobody placeholder
        with open(os.path.join(os.path.dirname(__file__), 'nobody.pem')) as f:
            nobody_pem = f.read()

        self.certs.add(nobody_pem)
        self.uids[get_der(nobody_pem)] = None

    def add_user(self, uname, pem_data=None, password=None,
                 security=kdf.hash_password, appname='zerodb.com'):
        root = persistent.mapping.PersistentMapping()
        self._p_jar.add(root)

        password, _ = security(
                uname, password,
                key_file=None, cert_file=None,
                appname=appname, key=None)

        user = User(uname, root, password)
        self.users[user.id] = user
        self.users_by_name[user.name] = user

        if pem_data:
            self._add_user_cert(user, pem_data)

        return user

    def _add_user_cert(self, user, pem_data):
        cert_der = get_der(pem_data)
        if cert_der in self.uids or cert_der in user.certs:
            raise ValueError("SSL certificate id already used",
                             pem_data, user.id)
        self.uids[cert_der] = user.id
        user.certs[cert_der] = pem_data
        self.certs.add(pem_data)

    def _del_user_certs(self, user):
        for der, pem_data in user.certs.items():
            del self.uids[der]
            self.certs.remove(pem_data)

    def del_user(self, name):
        user = self.users_by_name.pop(name)
        del self.users[user.id]
        self._del_user_certs(user)

    def change_cert(self, name, pem_data=None, password=None,
                    security=kdf.hash_password, appname='zerodb.com'):
        user = self.users_by_name[name]

        if pem_data is not None:
            self._del_user_certs(user)
            user.certs.clear()
            if pem_data:
                self._add_user_cert(user, pem_data)

        if password is not None:
            password, _ = security(
                    name, password,
                    key_file=None, cert_file=None,
                    appname=appname, key=None)
            user.change_password(password)


def get_admin(conn):
    return conn.get(ONE)


def init_db(storage, uname, pem_data=None, close=True, password=None):
    db = ZODB.DB(OwnerStorage(storage, p64(2)))
    with db.transaction() as conn:
        conn.root.admin = Admin(conn)
        user = conn.root.admin.add_user(uname, pem_data, password)
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
