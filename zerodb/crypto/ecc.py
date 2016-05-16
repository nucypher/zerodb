import six
import hashlib
# We can use pyelliptic (uses OpenSSL) but this is more cross-patform
import ecdsa

# We use curve standard for Bitcoin by default
DEFAULT_CURVE = "SECP256k1"


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


def private(seed, curve_name=DEFAULT_CURVE):
    try:
        curve = getattr(ecdsa.curves, curve_name)
        assert isinstance(curve, ecdsa.curves.Curve)
    except:
        raise ecdsa.curves.UnknownCurveError("I don't lnow this curve!")

    if six.PY3:
        if isinstance(seed, six.string_types):
            seed = seed.encode()

    priv = hashlib.sha512(seed).digest()[:curve.baselen]
    key = SigningKey.from_string(priv, curve=curve)
    return key


def public(pub, curve_name=DEFAULT_CURVE):
    try:
        curve = getattr(ecdsa.curves, curve_name)
        assert isinstance(curve, ecdsa.curves.Curve)
    except:
        raise ecdsa.curves.UnknownCurveError("I don't lnow this curve!")

    assert pub[0] == b'\x04'[0]
    return VerifyingKey.from_string(pub[1:], curve=curve)
