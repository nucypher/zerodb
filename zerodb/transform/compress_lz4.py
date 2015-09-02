import lz4
from compress_common import CommonCompressor

lz4_compressor = CommonCompressor(name="lz4", compress=lz4.compress, decompress=lz4.uncompress)
