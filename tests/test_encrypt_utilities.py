from zerodb.transform import init_crypto, encrypt, decrypt
from zerodb.transform.encrypt_aes import AES256Encrypter


def test_utilities():
    AES256Encrypter.register_class(default=True)

    init_crypto(passphrase="Hello world")

    test_text = b"Test text " * 100

    encrypted_text = encrypt(test_text)
    assert encrypted_text.startswith(b".e")
    assert decrypt(encrypted_text) == test_text
