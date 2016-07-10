import six
import hashlib
import ecdsa  # We can use pyelliptic (uses OpenSSL) but this is more cross-patform

# We use curve standard for Bitcoin by default
CURVE = ecdsa.SECP256k1


class SigningKey(ecdsa.SigningKey, object):
    def get_pubkey(self):
        return b'\x04' + self.get_verifying_key().to_string()

    def sign(self, msg):
        return super(SigningKey, self).sign(
                msg,
                sigencode=ecdsa.util.sigencode_der,
                hashfunc=hashlib.sha256)


class VerifyingKey(ecdsa.VerifyingKey, object):
    def verify(self, signature, data):
        return super(VerifyingKey, self).verify(
                signature, data,
                hashfunc=hashlib.sha256,
                sigdecode=ecdsa.util.sigdecode_der)


def private(seed, salt, kdf=None, curve=CURVE):
    assert callable(kdf)
    if six.PY3 and isinstance(seed, six.string_types):
        seed = seed.encode()
    if isinstance(salt, (list, tuple)):
        salt = "|".join(salt)
        if six.PY3:
            salt = salt.encode()

    return SigningKey.from_string(kdf(seed, salt), curve=curve)


def public(pub, curve=CURVE):
    assert pub[0] == b'\x04'[0]
    return VerifyingKey.from_string(pub[1:], curve=curve)
