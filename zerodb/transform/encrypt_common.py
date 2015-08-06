from zope.component import getGlobalSiteManager, ComponentLookupError
from zope.interface import implementer
from interfaces import IEncrypter, IEncrypterClass

_gsm = getGlobalSiteManager()


@implementer(IEncrypter)
class CommonEncrypter(object):
    name = ""
    attributes = ()

    def __init__(self, **kw):
        kwargs = {}
        for i in self.attributes:
            if i in kw:
                kwargs[i] = kw[i]
        self._signature = ".e%s$" % self.name
        self._init_encryption(**kwargs)
        self.register()

    def _init_encryption(self, **kw):
        pass

    def encrypt(self, data):
        if not data.startswith(self._signature):
            encrypted = self._signature + self._encrypt(data)
            return encrypted
        else:
            return data

    def decrypt(self, data):
        if data.startswith(self._signature):
            return self._decrypt(data[len(self._signature):])
        else:
            return data

    def register(self):
        try:
            if _gsm.getUtility(IEncrypterClass) is self.__class__:
                _gsm.registerUtility(self)
            _gsm.registerUtility(self, name=self.name)
        except ComponentLookupError:
            pass

    @classmethod
    def register_class(self, default=False):
        _gsm.registerUtility(self, IEncrypterClass, name=self.name)
        if default:
            _gsm.registerUtility(self, IEncrypterClass)


def encrypt(data):
    try:
        return _gsm.getUtility(IEncrypter).encrypt(data)
    except ComponentLookupError:
        return data


def decrypt(data):
    if data.startswith(".e"):
        name = data[2:data.find("$")]
        return _gsm.getUtility(IEncrypter, name).decrypt(data)
    else:
        return data


def init(**kw):
    for name, cls in _gsm.getUtilitiesFor(IEncrypterClass):
        if name:
            try:
                utility = _gsm.getUtility(IEncrypter, name=name)
                _gsm.unregisterUtility(utility)
            except ComponentLookupError:
                pass
            cls(**kw).register()
