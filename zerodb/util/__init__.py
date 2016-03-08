import six


def encode_hex(data):
    if six.PY2:
        return data.encode('hex')
    else:
        return data.hex()
