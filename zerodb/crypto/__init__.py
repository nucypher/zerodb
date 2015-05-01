from aes import AES
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
