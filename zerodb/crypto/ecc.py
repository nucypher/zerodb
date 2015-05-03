import pyelliptic as pe  # This module re-uses OPENSSL's code
import ecdsa  # But this one is more functional :-)
from zerodb.crypto import sha256


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
    priv = sha256("elliptic" + sha256(passphrase))
    px, py = priv2pub(priv)
    key = pe.ECC(curve=CURVE)
    key._set_keys(px, py, priv)
    return key


def public(pub):
    return pe.ECC(curve=CURVE, pubkey=pub)
