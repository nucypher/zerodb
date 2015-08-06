from Crypto.Cipher import AES as CryptoAES
from Crypto import Random
from hashlib import sha256
import struct

from zerodb.crypto.afgh_pre import afgh_pre
from zerodb.crypto.exceptions import WrongKeyError
from encrypt_common import CommonEncrypter


class AFGHEncrypter(CommonEncrypter):
    """
    AFGH proxy re-encryption combined with AES.
    This class is to encrypt and decrypt whatever is encrypted for us
    """
    name = "afgh1-aes"
    attributes = ("passphrase", "key")

    # AES parameters
    iv_size = 16
    aes_key_size = 32
    hash_size = 32
    aes_mode = CryptoAES.MODE_CFB

    afgh_key_size = 32
    afgh_decrypt_method = "decrypt_my"

    def _init_encryption(self, passphrase=None, key=None):
        """
        :param str passphrase: Passphrase for encryption (use if no key is set)
        :param str key: Symmetric key (if passphrase is not set)
        """
        if passphrase is not None:
            assert key is None
            self.afgh_key = afgh_pre.Key.from_passphrase(passphrase)
        elif key is not None:
            assert len(key) == self.afgh_key_size
            self.afgh_key = afgh_pre.Key.load_priv(key)
        self._decrypt_method = getattr(self.afgh_key, self.afgh_decrypt_method)
        self._rand = Random.new()

    def _encrypt(self, data):
        iv = self._rand.read(self.iv_size)
        aes_key = self._rand.read(self.aes_key_size)
        aes_cipher = CryptoAES.new(aes_key, self.aes_mode, iv)
        h = sha256(data).digest()
        edata = aes_cipher.encrypt(data + h) + iv
        kdata = self.afgh_key.encrypt(aes_key)
        len_kdata = struct.pack("H", len(kdata))
        return len_kdata + kdata + edata

    def _decrypt(self, edata):
        len_kdata, = struct.unpack("H", edata[:2])
        kdata = edata[2:len_kdata + 2]
        adata = edata[len_kdata + 2:-self.iv_size]
        iv = edata[-self.iv_size:]
        aes_key = self._decrypt_method(kdata)
        if len(aes_key) != self.aes_key_size:
            raise WrongKeyError("Data couldn't be decrypted. Probably your key is wrong")
        aes_cipher = CryptoAES.new(aes_key, self.aes_mode, iv)
        datah = aes_cipher.decrypt(adata)
        h = datah[-self.hash_size:]
        data = datah[:-self.hash_size]
        if sha256(data).digest() == h:
            return data
        else:
            raise WrongKeyError("Data couldn't be decrypted. Probably your key is wrong")

    def get_pubkey(self):
        return self.afgh_key.dump_pub()

    def get_re_key(self, pub):
        return self.afgh_key.re_key(pub).dump()


class AFGHEncrypterRe(AFGHEncrypter):
    name = "afgh2-aes"
    afgh_decrypt_method = "decrypt_re"

    def _encrypt(self, data):
        raise NotImplementedError("This is used only to decrypt re-encrypted data")


class AFGHReEncryption(object):
    sig1 = ".eafgh1-aes$"
    sig2 = ".eafgh2-aes$"

    def __init__(self, re_key_dump):
        self.key = afgh_pre.ReKey.load(re_key_dump)

    def reencrypt(self, edata):
        if edata.startswith(self.sig1):
            edata = edata[len(self.sig1):]
            len_kdata, = struct.unpack("H", edata[:2])
            kdata = edata[2:len_kdata + 2]
            tail = edata[len_kdata + 2:]
            kdata = self.key.reencrypt(kdata)
            len_kdata = struct.pack("H", len(kdata))
            return self.sig2 + len_kdata + kdata + tail
        else:
            raise ValueError("Not encrypted with AFGH algoithm")
