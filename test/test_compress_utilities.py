from zerodb.transform import compress, decompress
from zerodb.transform.compress_zlib import zlib_compressor


def test_utilities():
    zlib_compressor.register(default=True)
    test_string = b"This is a test " * 1000

    compressed_default = compress(test_string)
    compressed_zlib = zlib_compressor.compress(test_string)

    assert compressed_default == compressed_zlib
    assert compressed_default != test_string
    assert compressed_zlib != test_string

    assert decompress(compressed_default) == test_string
    assert decompress(compressed_zlib) == test_string
