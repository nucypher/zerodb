from Crypto.Hash import SHA256
from Crypto.Cipher import AES as CryptoAES
from Crypto import Random


class AES(object):
    """
    Object which encrypts and decrypts data with AES algorithm
    """
    iv_size = 16  # Presumably depends on the mode though

    def __init__(self, passphrase=None, key=None, size=32):
        if passphrase is not None:
            assert key is None
            assert size <= 32
            self.key = SHA256.new(passphrase).digest()[:size]
        elif key is not None:
            self.key = key
        self.mode = CryptoAES.MODE_CFB  # Need to support other modes
        self._rand = Random.new()

    def encrypt(self, data):
        iv = self._rand.read(self.iv_size)
        cipher = CryptoAES.new(self.key, self.mode, iv)
        return cipher.encrypt(data) + iv  # with modes other than CFB we'd need to pad/unpad data
        # XXX need to error out with "wrong key" if it's wrong, so need to encrypt hash as well

    def decrypt(self, edata):
        data = edata[:-self.iv_size]
        iv = edata[-self.iv_size:]
        cipher = CryptoAES.new(self.key, self.mode, iv)
        return cipher.decrypt(data)
