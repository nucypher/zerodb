from .db import DB

def server(path=None, blob_dir=None, storage_conf=None, zeo_conf=None,
           port=0, threaded=True, **kw):
    import os, zerodb.forker
    if storage_conf is None and path is None:
        storage_conf = '<mappingstorage>\n</mappingstorage>'

    return zerodb.forker.start_server(
        storage_conf, zeo_conf, port, keep=True, path=path,
        blob_dir=blob_dir, suicide=False, threaded=threaded, **kw)
