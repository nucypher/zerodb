"""Test new SSL-based access
"""
import os

import pytest

from ZODB.utils import z64, maxtid
import transaction
import ZEO
import ZEO.tests.testssl
import ZODB.POSException

import zerodb
import zerodb.forker
import zerodb.permissions.base

here = os.path.dirname(__file__)
pem_path = lambda name: os.path.join(here, name + '.pem')
def pem_data(name):
    with open(pem_path(name)) as f:
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

        [uid0] = [uid for uid in conn.root.users if uid != z64]

    admin_db.close()

    # Now, let's try connecting
    db = zerodb.DB(addr,
                   cert_file=pem_path('cert0'), key_file=pem_path('key0'),
                   server_cert=ZEO.tests.testssl.server_cert,
                   password='5ecret')

    # we can access the root object.
    assert db._root._p_oid == uid0

    # It's empty now:
    assert len(db._root) == 0

    # Let's put something it:
    db._root['x'] = 1
    db._root['s'] = db._root.__class__()
    db._root['s']['x'] = 2

    db._connection.transaction_manager.commit()

    # Close the db and reopen:
    db._db.close()

    # Reopen, and make sure the data are there:
    db = zerodb.DB(addr,
                   cert_file=pem_path('cert0'), key_file=pem_path('key0'),
                   server_cert=ZEO.tests.testssl.server_cert,
                   password='5ecret')

    assert db._root._p_oid == uid0
    assert len(db._root) == 2
    assert db._root['x'] == 1
    assert db._root['s']['x'] == 2
    s0 = db._root._p_serial
    db._db.close()

    # The admin user can no longer access the user's folder:
    admin_db = ZEO.DB(addr, ssl = ZEO.tests.testssl.client_ssl())
    with admin_db.transaction() as conn:
        admin_db.storage._cache.clear()
        conn.cacheMinimize()
        user_root = conn.root.users[uid0].root
        with pytest.raises(ZODB.POSException.StorageError) as exc_info:
            len(user_root)

        assert ('Attempt to access encrypted data of others'
                in str(exc_info.value))

    admin_db.close()

    # The user's data are encrypted:
    server_server = zerodb.forker.last_server
    storage = server_server.server.storages['1']
    assert storage.loadBefore(uid0, maxtid)[0].startswith(b'.e')

    stop()
