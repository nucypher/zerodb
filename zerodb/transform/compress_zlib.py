import zlib
from compress_common import CommonCompressor

zlib_compressor = CommonCompressor(name="zlib", compress=zlib.compress, decompress=zlib.decompress)
