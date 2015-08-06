import pytest


def test_utility():
    from zerodb.transform.encrypt_afgh import AFGHEncrypter, WrongKeyError, AFGHEncrypterRe, AFGHReEncryption

    utility1 = AFGHEncrypter(passphrase="Hello world")
    utility2 = AFGHEncrypter(passphrase="Hello world")
    utility3 = AFGHEncrypter(passphrase="Other password")
    utility3_ = AFGHEncrypterRe(passphrase="Other password")

    test_text = "Test text " * 100

    encrypted_text = utility1.encrypt(test_text)

    pub3 = utility3.get_pubkey()
    re_1_3 = utility1.get_re_key(pub3)

    re_key = AFGHReEncryption(re_1_3)
    re_text = re_key.reencrypt(encrypted_text)

    assert encrypted_text.startswith(".e")
    assert utility1.decrypt(encrypted_text) == test_text
    assert utility2.decrypt(encrypted_text) == test_text
    with pytest.raises(WrongKeyError):
        utility3.decrypt(encrypted_text)
    assert utility3_.decrypt(re_text) == test_text
