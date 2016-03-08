import six
from hashlib import sha256

from .encrypt_common import CommonEncrypter
from Crypto.Random import get_random_bytes as rand
from zerodb.crypto.exceptions import WrongKeyError

import logging

try:
    from zerodbext.aead import AES256GCM
    from zerodbext.aead.bindings import crypto_aead_aes256gcm_ABYTES as MAC_LEN
    import zerodbext.aead.exceptions
    CryptoError = (zerodbext.aead.exceptions.CryptoError, ValueError)
    use_sodium = True

except ImportError:
    CryptoError = ValueError
    use_sodium = False

finally:
    from Crypto.Cipher import AES
    if hasattr(AES, "MODE_GCM"):
        MODE = AES.MODE_GCM
    else:
        if use_sodium:
            logging.info("Old AES256 with IV_SIZE=16 will not work")
        else:
            raise ImportError("You need to have PyCryptoDome which has support for AES256-GCM")


class AES256Encrypter(CommonEncrypter):
    """
    AES256 with key derived as sha256(passphrase)
    """
    name = b"AES256-GCM"
    attributes = ("passphrase", "key")
    iv_size = 12
    key_size = 32

    use_sodium = use_sodium

    def _init_encryption(self, passphrase=None, key=None):
        """
        :param str passphrase: Passphrase for encryption (use if no key is set)
        :param str key: Symmetric key (if passphrase is not set)
        """
        if passphrase is not None:
            assert key is None
            if six.PY3 and isinstance(passphrase, str):
                passphrase = passphrase.encode()
            key = sha256(passphrase).digest()
        elif key is not None:
            assert len(key) == self.key_size

        if self.use_sodium:
            self._box = AES256GCM(key)
        else:
            self.key = key

    def _encrypt(self, data):
        """
        :param str data: Data to encrypt
        :return: Encrypted data with hash inside and IV outside
        :rtype: str
        """
        iv = rand(self.iv_size)
        if self.use_sodium:
            edata, tag = self._box.encrypt_and_mac(data, iv)
        else:
            cipher = AES.new(self.key, MODE, iv)
            edata, tag = cipher.encrypt_and_digest(data)
        return iv + bytes(tag) + bytes(edata)

    def _decrypt(self, edata):
        """
        :param str edata: Data to decrypt
        :return: Decrypted data
        :rtype: str
        """
        f = six.BytesIO(edata)
        iv = f.read(self.iv_size)
        if self.use_sodium:
            tag = f.read(MAC_LEN)
        else:
            cipher = AES.new(self.key, MODE, iv)
            tag = f.read(cipher._mac_len)
        data = f.read(-1)
        try:
            if self.use_sodium:
                return bytes(self._box.decrypt_and_verify(data, tag, iv))
            else:
                return bytes(cipher.decrypt_and_verify(data, tag))
        except CryptoError:
            raise WrongKeyError("Data couldn't be decrypted. Probably your key is wrong")


class AES256EncrypterV0(AES256Encrypter):
    name = b"AES256"
    use_sodium = False
    iv_size = 16
