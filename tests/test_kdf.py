from zerodb.crypto import kdf
import ZEO

test_key = b'x' * 32

test_args_1 = dict(
        username='user1', password='password1',
        key_file=ZEO.tests.testssl.client_key,
        cert_file=ZEO.tests.testssl.client_cert,
        appname='zerodb.com', key=test_key)

test_args_2 = dict(
        username='user1', password='password2',
        key_file=ZEO.tests.testssl.client_key,
        cert_file=ZEO.tests.testssl.client_cert,
        appname='zerodb.com', key=test_key)


def test_kdfs():
    # Test that all methods give the same password hash
    kfp_password, kfp_key = kdf.key_from_password(**test_args_1)
    kfc_password, kfc_key = kdf.key_from_cert(**test_args_1)
    hash_password, hash_key = kdf.hash_password(**test_args_1)

    # Password hash should be always the same (!)
    assert kfp_password == kfc_password == hash_password

    # Last one doesn't touch key
    assert hash_key == test_key

    # All methods make different encryption keys
    assert len(set([kfp_key, kfc_key, hash_key])) == 3

    kfp_password_2, kfp_key_2 = kdf.key_from_password(**test_args_2)
    assert kfp_password_2 != kfp_password
    assert kfp_key_2 != kfp_key

    kfc_password_2, kfc_key_2 = kdf.key_from_cert(**test_args_2)
    assert kfc_password_2 != kfc_password
    assert kfc_key_2 == kfc_key

    hash_password_2, hash_key_2 = kdf.hash_password(**test_args_2)
    assert hash_password_2 != hash_password
    assert hash_key == test_key

    assert kfp_password_2 == kfc_password_2 == hash_password_2

    assert kfp_password != test_args_1['password']
    assert kfp_password_2 != test_args_2['password']
