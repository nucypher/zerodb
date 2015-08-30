from Crypto.Hash import SHA256, SHA512
from Crypto import Random

_rng = Random.new()


def rand(size):
    """
    Generate a random string. In a cryptographically secure way

    :param int size: How many bytes to generate
    :return: Random string
    :rtype: str
    """
    return _rng.read(size)


def sha256(s):
    """
    SHA256 hash of string s

    :param str s: Input string
    :return: Digest of it
    """
    return SHA256.new(s).digest()


def sha512(s):
    """
    SHA512 hash of string s

    :param str s: Input string
    :return: Digest of it
    """
    return SHA512.new(s).digest()
