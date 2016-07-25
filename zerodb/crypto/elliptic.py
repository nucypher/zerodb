import ecdsa
import scrypt


# XXX move somewhere else
def kdf(seed, salt):
    return scrypt.hash(seed, salt)[:ecdsa.SECP256k1.baselen]
