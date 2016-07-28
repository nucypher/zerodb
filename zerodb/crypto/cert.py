# Tools to generate certificates from keys
from OpenSSL import crypto
import ecdsa
import hashlib
import os
import ssl
import tempfile

DEFAULT_CURVE = "NIST256p"


def pkey2cert(key, curve=DEFAULT_CURVE, CN="zerodb.com"):
    curve = getattr(ecdsa.curves, curve)
    if not isinstance(key, bytes):
        key = key.encode()
    serial = int.from_bytes(
            hashlib.sha256(key).digest()[:8], byteorder="little")

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

    priv_pem = crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode()
    pub_pem = crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode()

    return priv_pem, pub_pem


def ssl_context_from_key(key, server_cert):
    ssl_context = ssl.create_default_context(cafile=server_cert)

    priv_pem, pub_pem = pkey2cert(key)

    f_priv = tempfile.NamedTemporaryFile(delete=False)
    f_priv.write(priv_pem.encode())
    f_priv.close()
    f_pub = tempfile.NamedTemporaryFile(delete=False)
    f_pub.write(pub_pem.encode())
    f_pub.close()

    try:
        ssl_context.load_cert_chain(f_pub.name, f_priv.name)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_REQUIRED
    finally:
        os.remove(f_priv.name)
        os.remove(f_pub.name)

    return ssl_context
