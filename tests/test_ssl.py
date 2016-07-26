"""Test new SSL-based access
"""
import os

import pytest

from ZODB.utils import z64, maxtid
import transaction
import ZEO
import ZEO.Exceptions
import ZEO.tests.testssl
import ZODB.POSException

import zerodb
import zerodb.forker
import zerodb.permissions.base

##
import logging
logging.basicConfig(level=logging.DEBUG)
##

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

        # The get_admin function gets us an admin object with CRUD methods.
        admin = zerodb.permissions.base.get_admin(conn)
        [root] = admin.users.values()
        [root_der] = root.certs
        assert admin.certs.data.strip() == root.certs[root_der].strip()
        assert admin.uids[root_der] == root.id
        assert len(admin.uids) == 1
        assert len(admin.users_by_name) == 1
        assert admin.users_by_name[root.name] is root

        # Let's add a user:
        admin.add_user('user1', pem_data=pem_data('cert0'))
        admin.add_user('user2', password='much secret wow')

        [uid0] = [uid for uid in admin.users if uid != root.id]

    admin_db.close()

    # Now, let's try connecting
    db = zerodb.DB(addr,
                   cert_file=pem_path('cert0'), key_file=pem_path('key0'),
                   server_cert=ZEO.tests.testssl.server_cert,
                   username='user1', password='5ecret')

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
                   username='user1', password='5ecret')

    assert db._root._p_oid == uid0
    assert len(db._root) == 2
    assert db._root['x'] == 1
    assert db._root['s']['x'] == 2
    s0 = db._root._p_serial
    db._db.close()

    # The admin user can no longer access the user's folder:
    admin_db = ZEO.DB(addr, ssl = ZEO.tests.testssl.client_ssl())
    with admin_db.transaction() as conn:
        admin = zerodb.permissions.base.get_admin(conn)
        user_root = admin.users[uid0].root
        with pytest.raises(ZODB.POSException.StorageError) as exc_info:
            len(user_root)

        assert ('Attempt to access encrypted data of others'
                in str(exc_info.value))

    # Note that we had to close and reopen the admin connection
    # because invalidations aren't sent accross users. (Even clearing
    # the cache doesn't work (maybe a misfeature))

    # The user's data are encrypted:
    server_server = zerodb.forker.last_server
    storage = server_server.server.storages['1']
    assert storage.loadBefore(uid0, maxtid)[0].startswith(b'.e')

    # Let's change the user's cert:

    with admin_db.transaction() as conn:
        admin = zerodb.permissions.base.get_admin(conn)
        admin.change_cert('user1', pem_data('cert1'))

    # Now login with the old cert will fail:
    with pytest.raises(ZEO.Exceptions.ClientDisconnected):
        db = zerodb.DB(addr,
                       cert_file=pem_path('cert0'), key_file=pem_path('key0'),
                       server_cert=ZEO.tests.testssl.server_cert,
                       username='user1', password='5ecret', wait_timeout=1)

    # But login with the new one will work:
    db = zerodb.DB(addr,
                   cert_file=pem_path('cert1'), key_file=pem_path('key1'),
                   server_cert=ZEO.tests.testssl.server_cert,
                   username='user1', password='5ecret', wait_timeout=1)
    assert len(db._root) == 2
    db._db.close()

    # Finally, let's remove the user:
    with admin_db.transaction() as conn:
        admin = zerodb.permissions.base.get_admin(conn)
        admin.del_user('user1')

    # Now, they can't log in at all:
    for i in '01':
        with pytest.raises(ZEO.Exceptions.ClientDisconnected):
            db = zerodb.DB(
                addr,
                cert_file=pem_path('cert' + i), key_file=pem_path('key' + i),
                server_cert=ZEO.tests.testssl.server_cert,
                username='user1', password='5ecret', wait_timeout=1)

    admin_db.close()

    # Authentification by password
    raise
    db = zerodb.DB(addr, username='user2', password='much secret wow',
                   server_cert=ZEO.tests.testssl.server_cert, wait_timeout=1)
    db._db.close()

    stop()
