from aes import AES
from Crypto import Random

_rng = Random.new()


def rand(size):
    return _rng.read(size)
