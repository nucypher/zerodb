"""Test user statistic script
"""
import os
import ZEO
import ZEO.tests.testssl

import zerodb
import zerodb.permissions.base

from zerodb.crypto import kdf
from zerodb.permissions.userstats import userstats

here = os.path.dirname(__file__)
pem_path = lambda name: os.path.join(here, name + '.pem')

def pem_data(name):
    with open(pem_path(name)) as f:
        return f.read()

root_key = b'r' * 32
user_key = b'x' * 32

def test_userstats(tempdir):

    path = os.path.join(tempdir, 'data.fs')

    addr, stop = zerodb.server(path=path)

    admin_db = ZEO.DB(addr,ssl=ZEO.tests.testssl.client_ssl())
    with admin_db.transaction() as conn:

        # The get_admin function gets us an admin object with CRUD methods.
        admin = zerodb.permissions.base.get_admin(conn)
        admin.add_user('user0', pem_data=(pem_data('cert0')))
        admin.add_user('user1', pem_data=(pem_data('cert1')))
    admin_db.close()

    # Now, let's try connecting
    def user_db_factory(n='0'):
        return zerodb.DB(
            addr, username='user'+n, key=user_key,
            cert_file=pem_path('cert' + n),
            key_file=pem_path('key' + n),
            server_cert=ZEO.tests.testssl.server_cert,
            )

    for u in '01':
        db = user_db_factory(u)
        for j in range(3):
            db._root[j] = db._root.__class__()
            db._root[j]['x'] = 'x' * (500 * int(u) + 1)
            db._connection.transaction_manager.commit()
        db._db.close()

    stats = userstats(path)

    assert sorted(stats) == [
        (b'\x00\x00\x00\x00\x00\x00\x00\x02', 'root', 23759),
        (b'\x00\x00\x00\x00\x00\x00\x00\x08', 'user0', 1151),
        (b'\x00\x00\x00\x00\x00\x00\x00\t', 'user1', 2669),
        ]

    stop()
