from cStringIO import StringIO
from Crypto.Cipher import AES
from hashlib import sha256

from encrypt_common import CommonEncrypter
from Crypto.Random import get_random_bytes as rand
from zerodb.crypto.exceptions import WrongKeyError


class AES256Encrypter(CommonEncrypter):
    """
    AES256 with key derived as sha256(passphrase)
    """
    name = "AES256"
    attributes = ("passphrase", "key")
    iv_size = 16
    key_size = 32
    hash_size = 32
    mode = AES.MODE_GCM

    def _init_encryption(self, passphrase=None, key=None):
        """
        :param str passphrase: Passphrase for encryption (use if no key is set)
        :param str key: Symmetric key (if passphrase is not set)
        """
        if passphrase is not None:
            assert key is None
            self.key = sha256(passphrase).digest()
        elif key is not None:
            assert len(key) == self.key_size
            self.key = key

    def _encrypt(self, data):
        """
        :param str data: Data to encrypt
        :return: Encrypted data with hash inside and IV outside
        :rtype: str
        """
        iv = rand(self.iv_size)
        cipher = AES.new(self.key, self.mode, iv)
        edata, tag = cipher.encrypt_and_digest(data)
        return iv + tag + edata

    def _decrypt(self, edata):
        """
        :param str edata: Data to decrypt
        :return: Decrypted data
        :rtype: str
        """
        f = StringIO(edata)
        iv = f.read(self.iv_size)
        cipher = AES.new(self.key, self.mode, iv)
        tag = f.read(cipher._mac_len)
        data = f.read(-1)
        try:
            return cipher.decrypt_and_verify(data, tag)
        except ValueError:
            raise WrongKeyError("Data couldn't be decrypted. Probably your key is wrong")
