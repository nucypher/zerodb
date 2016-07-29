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
import zerodb.db
import zerodb.forker
import zerodb.permissions.base

here = os.path.dirname(__file__)
pem_path = lambda name: os.path.join(here, name + '.pem')
def pem_data(name):
    with open(pem_path(name)) as f:
        return f.read()

nobody_dir = os.path.dirname(zerodb.permissions.__file__)
nobody_cert = os.path.join(nobody_dir, 'nobody.pem')
nobody_pem = pem_data(nobody_cert[:-4])
def nobody_ssl():
    return zerodb.db.make_ssl(server_cert=ZEO.tests.testssl.server_cert)

def _test_basic(root_cert=True, root_password=False,
                user_cert=True, user_password=False,
                ):
    # zerodb.server took care of setting up a databasw with a root
    # user and starting a server for it.  The root user's cert is from
    # ZEO.testing.  The server is using a server cert from ZEO.tests.
    addr, stop = zerodb.server(
        init=dict(
            cert = ZEO.tests.testssl.client_cert if root_cert else None,
            password='root_password' if root_password else None,
            ),
        )

    # Create an admin client.  Admin data aren't encrypted, so we use
    # a regular ZEO client.
    def admin_db_factory():
        return ZEO.DB(
            addr,
            ssl = ZEO.tests.testssl.client_ssl() if root_cert else nobody_ssl(),
            credentials =
            dict(name='root', password='root_password')
            if root_password else None,
            wait_timeout=19999,
            )

    admin_db = admin_db_factory()
    with admin_db.transaction() as conn:

        # The get_admin function gets us an admin object with CRUD methods.
        admin = zerodb.permissions.base.get_admin(conn)
        [root] = admin.users.values()
        if root_cert:
            [root_der] = root.certs

            assert (set(pem.strip()
                        for pem in admin.certs.data.strip().split('\n\n'))
                    ==
                    set(pem.strip()
                        for pem in (nobody_pem, root.certs[root_der]))
                    )
            assert admin.uids[root_der] == root.id
        else:
            assert admin.certs.data.strip() == nobody_pem.strip()
        assert len(admin.uids) == 2 if root_cert else 1
        assert len(admin.users_by_name) == 1
        assert admin.users_by_name[root.name] is root

        # Let's add a user:
        admin.add_user('user0',
                       pem_data = pem_data('cert0') if user_cert else None,
                       password = 'password0' if user_password else None,
                       )

        [uid0] = [uid for uid in admin.users if uid != root.id]

    admin_db.close()

    # Now, let's try connecting
    def user_db_factory(n='0'):
        return zerodb.DB(
            addr, username='user0', key='secret0',
            cert_file=pem_path('cert'+n) if user_cert else None,
            key_file=pem_path('key'+n) if user_cert else None,
            server_cert=ZEO.tests.testssl.server_cert,
            password='password'+n if user_password else None,
            wait_timeout=1
            )

    db = user_db_factory()

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
    db = user_db_factory()

    assert db._root._p_oid == uid0
    assert len(db._root) == 2
    assert db._root['x'] == 1
    assert db._root['s']['x'] == 2
    s0 = db._root._p_serial
    db._db.close()

    # The admin user can no longer access the user's folder:
    admin_db = admin_db_factory()
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

    # Let's change the user's credentials:

    with admin_db.transaction() as conn:
        admin = zerodb.permissions.base.get_admin(conn)
        admin.change_cert(
            'user0',
            pem_data('cert1') if user_cert else None,
            'password1' if user_password else None,
            )

    # Now login with the old cert will fail:
    with pytest.raises(ZEO.Exceptions.ClientDisconnected):
        user_db_factory()

    # But login with the new one will work:
    db = user_db_factory('1')
    assert len(db._root) == 2
    db._db.close()

    # Finally, let's remove the user:
    with admin_db.transaction() as conn:
        admin = zerodb.permissions.base.get_admin(conn)
        admin.del_user('user0')

    # Now, they can't log in at all:
    for i in '01':
        with pytest.raises(ZEO.Exceptions.ClientDisconnected):
            user_db_factory(i)

    admin_db.close()

    # The admin user can login as an ordinary ZeroDB user:
    db = zerodb.DB(
        addr, username='root', key='root_secret',
        cert_file=ZEO.tests.testssl.client_cert if root_cert else None,
        key_file=ZEO.tests.testssl.client_key if root_cert else None,
        server_cert=ZEO.tests.testssl.server_cert,
        password='root_password' if root_password else None,
        wait_timeout=1
        )
    # They have an empty root
    assert len(db._root) == 0

    stop()

def test_cert_auth():
    _test_basic()

def test_pw_auth():
    _test_basic(False, True, False, True)

def test_mixed_auth():
    _test_basic(True, False, False, True)

def test_both():
    _test_basic(True, True, True, True)

def test_user_cred_crud_edge_cases():

    import ZODB.MappingStorage
    storage = ZODB.MappingStorage.MappingStorage()

    import zerodb.permissions.base

    pem = pem_data('cert0')
    zerodb.permissions.base.init_db(storage, 'boss', pem, False, 'pw')

    db = ZODB.DB(storage)
    with db.transaction() as conn:
        admin = zerodb.permissions.base.get_admin(conn)
        user = admin.users_by_name['boss']
        user.check_password('pw')
        assert list(user.certs.values()) == [pem]

        # No change if no cert or password passed
        admin.change_cert('boss')
        user.check_password('pw')
        assert list(user.certs.values()) == [pem]

        # Delete if false is padded
        admin.change_cert('boss', False, False)
        assert not user.certs
        assert user.password is None
