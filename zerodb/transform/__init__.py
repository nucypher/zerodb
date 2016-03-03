from . import compress_common
from . import encrypt_common

compress = compress_common.compress
decompress = compress_common.decompress
encrypt = encrypt_common.encrypt
decrypt = encrypt_common.decrypt
init_crypto = encrypt_common.init
