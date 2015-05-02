import pytest
from os import path
from zerodb.permissions.digest import PermissionsDatabase, passhash

TEST_PASSWORD = "v3ry 53cr3t pa$$w0rd"
TEST_PERMISSIONS = """realm ZERO
root:%s""" % passhash.encrypt(TEST_PASSWORD)


@pytest.fixture(scope="module")
def pass_file(request, tempdir):
    filename = path.join(tempdir, "authdb.conf")
    with open(filename, "w") as f:
        f.write(TEST_PERMISSIONS)
    return filename


@pytest.fixture(scope="module")
def pass_db(request, pass_file):
    db = PermissionsDatabase(pass_file)
    request.addfinalizer(db.close)
    return db


def test_root(pass_db):
    assert pass_db.verify_password("root", TEST_PASSWORD)
    assert not pass_db.verify_password("root", "wrong password")
    assert pass_db["root"].administrator
    with pytest.raises(LookupError):
        pass_db["attacker"]


def test_new(pass_db):
    pass_db.add_user("user1", "pass1temp", administrator=True)
    pass_db.add_user("user2", "pass2temp")
    pass_db.add_user("user3", "pass3")
    pass_db.del_user("user3")
    pass_db.change_password("user2", "pass2")
    pass_db._store_password("user4", "pass4")
    pass_db._store_password("user1", "pass1")

    assert pass_db.verify_password("user1", "pass1")
    assert pass_db.verify_password("user2", "pass2")
    with pytest.raises(LookupError):
        assert pass_db.verify_password("user3", "pass3")
    assert pass_db.verify_password("user4", "pass4")

    assert pass_db["user1"].administrator
    assert not pass_db["user2"].administrator
    assert not pass_db["user4"].administrator
