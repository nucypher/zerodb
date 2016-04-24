import six
import hashlib
import ecdsa  # We can use pyelliptic (uses OpenSSL) but this is more cross-patform

# We use curve standard for Bitcoin by default
CURVE_ecdsa = ecdsa.SECP256k1


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


def private(passphrase):
    if six.PY3 and isinstance(passphrase, six.string_types):
        passphrase = passphrase.encode()
    priv = hashlib.sha256(b"elliptic" + hashlib.sha256(passphrase).digest()).digest()
    key = SigningKey.from_string(priv, curve=CURVE_ecdsa)
    return key


def public(pub):
    assert pub[0] == b'\x04'[0]
    return VerifyingKey.from_string(pub[1:], curve=CURVE_ecdsa)
