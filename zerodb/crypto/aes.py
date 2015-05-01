from Crypto.Hash import SHA256
from Crypto.Cipher import AES as CryptoAES
from Crypto import Random
from zerodb.crypto.exceptions import WrongKeyError

HASH_SIZE = 32


class AES(object):
    """
    Object which encrypts and decrypts data with AES algorithm
    """
    iv_size = 16  # Presumably depends on the mode though

    def __init__(self, passphrase=None, key=None, size=32):
        """
        :param str passphrase: Passphrase for encryption (use if no key is set)
        :param str key: Symmetric key (if passphrase is not set)
        :param int size: Size of a key to make from passphrase
        """
        if passphrase is not None:
            assert key is None
            assert size <= 32
            self.key = SHA256.new(passphrase).digest()[:size]
        elif key is not None:
            self.key = key
        self.mode = CryptoAES.MODE_CFB  # Need to support other modes
        self._rand = Random.new()

    def encrypt(self, data):
        """
        :param str data: Data to encrypt
        :return: Encrypted data with hash inside and IV outside
        :rtype: str
        """
        iv = self._rand.read(self.iv_size)
        cipher = CryptoAES.new(self.key, self.mode, iv)
        h = SHA256.new(data).digest()
        return cipher.encrypt(data + h) + iv  # with modes other than CFB we'd need to pad/unpad data

    def decrypt(self, edata):
        """
        :param str edata: Data to decrypt
        :return: Decrypted data
        :rtype: str
        """
        data = edata[:-self.iv_size]
        iv = edata[-self.iv_size:]
        cipher = CryptoAES.new(self.key, self.mode, iv)
        datah = cipher.decrypt(data)
        h = datah[-HASH_SIZE:]
        data = datah[:-HASH_SIZE]
        if h != SHA256.new(data).digest():
            raise WrongKeyError("Data couldn't be decrypted. Probably your key is wrong")
        else:
            return data
