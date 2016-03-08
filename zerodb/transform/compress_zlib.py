import zlib
from .compress_common import CommonCompressor

zlib_compressor = CommonCompressor(name=b"zlib", compress=zlib.compress, decompress=zlib.decompress, args=[2])
