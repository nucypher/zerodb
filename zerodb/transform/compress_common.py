from zope.component import getGlobalSiteManager, ComponentLookupError
from zope.interface import implementer
from interfaces import ICompressor

_gsm = getGlobalSiteManager()


@implementer(ICompressor)
class CommonCompressor(object):
    """
    Common compression class
    One has to set _compress, _decompress and name
    """
    name = ""

    def __init__(self, name="", compress=None, decompress=None):
        self.name = name
        self._compress = compress
        self._decompress = decompress
        self._signature = self.name and ".c%s$" % self.name

    def compress(self, data):
        if not data.startswith(self._signature):
            compressed = self._signature + self._compress(data)
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
    if data.startswith(".c"):
        name = data[2:data.find("$")]
        return _gsm.getUtility(ICompressor, name).decompress(data)
    else:
        return data


def compress(data):
    try:
        return _gsm.getUtility(ICompressor).compress(data)
    except ComponentLookupError:
        return data
