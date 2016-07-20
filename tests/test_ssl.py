"""Test new SSL-based access
"""
import os

from ZODB.utils import z64
import ZEO
import ZEO.tests.testssl

import zerodb
import zerodb.permissions.base

here = os.path.dirname(__file__)
def pem_data(name):
    with open(os.path.join(here, name + '.pem')) as f:
        return f.read()

def test_basic():
    # zerodb.server took care of setting up a databasw with a root
    # user and starting a server for it.  The root user's cert is from
    # ZEO.testing.  The server is using a server cert from ZEO.tests.
    addr, stop = zerodb.server()

    # Create an admin client.  Admin data aren't encrypted, so we use
    # a regular ZEO client.
    admin_db = ZEO.DB(addr, ssl = ZEO.tests.testssl.client_ssl())
    with admin_db.transaction() as conn:
        root = conn.root.users[z64]
        assert len(conn.root.users) == 1
        [root_der] = root.certs
        assert len(root.certs) == 1
        assert conn.root.certs.data.strip() == root.certs[root_der].strip()
        assert conn.root.users_by_der[root_der] is root
        assert len(conn.root.users_by_der) == 1

        # Let's add a user:
        zerodb.permissions.base.add_user(conn, 'user1', pem_data('cert0'))

    admin_db.close()
    stop()
