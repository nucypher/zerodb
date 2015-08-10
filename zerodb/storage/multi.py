"""
Combine multiple server storages in one class
"""
from types import MethodType
from ZEO.StorageServer import ZEOStorage


class ServerStorageMeta(type):
    def __init__(cls, name, bases, dct):
        dct = dict(dct)
        extensions = set(cls.extensions)
        for base in reversed(bases):
            if hasattr(base, "extensions"):
                extensions.update(base.extensions)
            else:
                for attr in dir(base):
                    meth = getattr(base, attr)
                    if not attr.startswith("_") and isinstance(meth, MethodType) and not hasattr(ZEOStorage, attr):
                        extensions.add(meth)
        cls.extensions = list(extensions)
        super(ServerStorageMeta, cls).__init__(name, bases, dct)


class MultiStorage(ZEOStorage, object):
    __metaclass__ = ServerStorageMeta
