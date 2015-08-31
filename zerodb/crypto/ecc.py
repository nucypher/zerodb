import hashlib
import pyelliptic as pe  # This module re-uses OPENSSL's code
import ecdsa  # But this one is more functional :-)

# We can get rid of this pure-python ecdsa module and use compressed keys
# For OpenSSL-based implementation see:
#   https://github.com/Bitmessage/PyBitmessage/blob/master/src/highlevelcrypto.py
# For pure python implementation (just in case!) see:
#   https://github.com/vbuterin/pybitcointools/


# We use curve standard for Bitcoin by default
CURVE = "secp256k1"
CURVE_ecdsa = ecdsa.SECP256k1


def priv2pub(priv):
    """
    Converts 32-bytes private key to public key

    :param str priv: 32-byte private key
    :return: (pub_x, pub_y)
    :rtype: tuple
    """
    pub = ecdsa.SigningKey.from_string(priv, curve=CURVE_ecdsa).get_verifying_key().to_string()
    return pub[:32], pub[32:]


def private(passphrase):
    priv = hashlib.sha256("elliptic" + hashlib.sha256(passphrase).digest()).digest()
    px, py = priv2pub(priv)
    key = pe.ECC(curve=CURVE)
    key._set_keys(px, py, priv)
    return key


def public(pub):
    return pe.ECC(curve=CURVE, pubkey=pub)
