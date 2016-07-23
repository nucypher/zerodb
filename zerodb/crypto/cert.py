# Tools to generate certificates from keys
from OpenSSL import crypto
import ecdsa
import hashlib

DEFAULT_CURVE = "NIST256p"


def pkey2cert(key, curve=DEFAULT_CURVE, CN="zerodb.com"):
    curve = getattr(ecdsa.curves, curve)
    if not isinstance(key, bytes):
        key = key.encode()
    serial = int.from_bytes(
            hashlib.sha1(key).digest()[:8], byteorder="little")

    ecdsa_key = ecdsa.SigningKey.from_string(key, curve)
    k = crypto.load_privatekey(crypto.FILETYPE_PEM, ecdsa_key.to_pem())

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().CN = CN
    cert.set_serial_number(serial)
    cert.set_notBefore(b'20160722000000Z')
    cert.set_notAfter(b'20300101000000Z')
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    priv_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, k)
    pub_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)

    return priv_pem, pub_pem
