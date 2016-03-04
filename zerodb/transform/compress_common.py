from zope.component import getGlobalSiteManager, ComponentLookupError
from zope.interface import implementer
from .interfaces import ICompressor

_gsm = getGlobalSiteManager()


@implementer(ICompressor)
class CommonCompressor(object):
    """
    Common compression class
    One has to set _compress, _decompress and name
    """
    name = b""

    def __init__(self, name=b"", compress=None, decompress=None, args=None, kwargs=None):
        self.name = name
        self._compress = compress
        self._decompress = decompress
        self._signature = self.name and b".c%s$" % self.name
        self._args = args or []
        self._kwargs = kwargs or {}

    def compress(self, data):
        if not data.startswith(self._signature):
            compressed = self._signature + self._compress(data, *self._args, **self._kwargs)
            if len(compressed) < len(data):
                return compressed
        return data

    def decompress(self, data):
        if self._signature and data.startswith(self._signature):
            return self._decompress(data[len(self._signature):])
        else:
            return data

    def register(self, default=False):
        _gsm.registerUtility(self, name=self.name)
        if default:
            _gsm.registerUtility(self)


def decompress(data):
    if data.startswith(b".c"):
        name = data[2:data.find(b"$")].decode()
        return _gsm.getUtility(ICompressor, name).decompress(data)
    else:
        return data


def compress(data):
    try:
        return _gsm.getUtility(ICompressor).compress(data)
    except ComponentLookupError:
        return data
