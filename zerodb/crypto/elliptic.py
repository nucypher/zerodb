import ecdsa
import scrypt

def kdf(seed, salt):
    return scrypt.hash(seed, salt)[:ecdsa.SECP256k1.baselen]

