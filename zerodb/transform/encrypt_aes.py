from M2Crypto.EVP import Cipher
from hashlib import sha256

from encrypt_common import CommonEncrypter
from zerodb.crypto import rand
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
    alg = "aes_256_ofb"

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
        cipher = Cipher(alg=self.alg, key=self.key, iv=iv, op=1)
        h = sha256(data).digest()
        edata = cipher.update(data + h)
        edata += cipher.final()
        del cipher
        return edata + iv

    def _decrypt(self, edata):
        """
        :param str edata: Data to decrypt
        :return: Decrypted data
        :rtype: str
        """
        data = edata[:-self.iv_size]
        iv = edata[-self.iv_size:]
        cipher = Cipher(alg=self.alg, key=self.key, iv=iv, op=0)
        datah = cipher.update(data)
        datah += cipher.final()
        del cipher
        h = datah[-self.hash_size:]
        data = datah[:-self.hash_size]
        if h != sha256(data).digest():
            raise WrongKeyError("Data couldn't be decrypted. Probably your key is wrong")
        else:
            return data
