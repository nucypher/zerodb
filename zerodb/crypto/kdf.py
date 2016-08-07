"""
Key derivation/extraction functions.

Functions have form of:

def security_function(username, password, key_file, cert_file, appname, key):
    ...
    return password, key

Where key is 256-bit symmetric key, and new_password could be hash

We use scrypt to derive the key on the client side
"""
import scrypt
import hashlib

scrypt_kw = dict(N=16384, r=8, p=1, buflen=32)


def key_from_password(username, password, key_file, cert_file, appname, key):
    """
    Key is derived from password using scrypt
    password is replaced with sha256(key) so that we cannot deduce key from
    auth info
    """
    salt = "|".join([username, appname, 'key'])
    key = scrypt.hash(password, salt, **scrypt_kw)
    # Calculate hash so that server cannot derive key from new_password
    # b'auth' is added so that we don't use hash(key) by mistake
    new_password = hashlib.sha256(key + b'auth').digest()
    return new_password, key


def key_from_cert(username, password, key_file, cert_file, appname, key):
    """
    Key is derived from SSL key_file.
    Password is securely hashed if given at all
    """
    with open(key_file) as f:
        key = hashlib.sha256(f.read().encode()).digest()

    if password is not None:
        salt = "|".join([username, appname, 'key'])
        password = scrypt.hash(password, salt, **scrypt_kw)
        password = hashlib.sha256(password + b'auth').digest()

    return password, key


def hash_password(username, password, key_file, cert_file, appname, key):
    """
    Password is hashed, encryption key is left untouched.
    Password is compatible with other functions
    """
    if password:
        salt = "|".join([username, appname, 'key'])
        password = scrypt.hash(password, salt, **scrypt_kw)
        password = hashlib.sha256(password + b'auth').digest()

    return password, key


def guess(username, password, key_file, cert_file, appname, key):
    """
    Guess which function to use from values arguments
    """
    if key is None:
        if password is not None:
            return key_from_password
        elif key_file is not None:
            return key_from_cert
        else:
            raise AttributeError("Not enough attributes to guess KDF")

    else:
        return hash_password
