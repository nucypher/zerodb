from OpenSSL import crypto
from zerodb.crypto import cert
import ecdsa

sample_key = b'x' * 32


def test_pkey_to_cert():
    priv_pem, cert_pem = cert.pkey2cert(sample_key)

    # There is something
    assert len(priv_pem) > 0
    assert len(cert_pem) > 0

    cert_ssl = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem.decode())
    pub_ssl = cert_ssl.get_pubkey()

    # Certificate has only EC public key
    assert pub_ssl._only_public
    assert pub_ssl.type() == crypto._lib.EVP_PKEY_EC

    pub_pem = crypto.dump_publickey(crypto.FILETYPE_PEM, pub_ssl)
    pub = ecdsa.VerifyingKey.from_pem(pub_pem)

    # Manually generated public key is the same as in the certificate
    pub0 = ecdsa.SigningKey.from_string(
            sample_key, ecdsa.curves.NIST256p).get_verifying_key()
    assert pub.to_string() == pub0.to_string()
