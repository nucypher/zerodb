import persistent
from zope.index.text import widcode


class PersistentWid(persistent.Persistent):
    """
    Behaves like a string, but stored as a lazy-loaded persistent object.
    Can be encoded from word ids
    """

    def __init__(self, s):
        self.s = s

    @classmethod
    def encode_wid(cls, l):
        return cls(widcode.encode(l))

    def decode_wid(self):
        return widcode.decode(self.s)

    def __getattribute__(self, attr):
        try:
            return super(PersistentWid, self).__getattribute__(attr)
        except AttributeError:
            return super(PersistentWid, self).__getattribute__('s').__getattribute__(attr)
