import persistent
from zope.index.text import widcode
from zerodb.catalog.indexes import pwid


def test_wid():
    test_wids = list(range(5))
    pw = pwid.PersistentWid.encode_wid(test_wids)
    assert isinstance(pw, persistent.Persistent)
    assert pw.decode_wid() == test_wids
    assert pw.find(widcode.encode([1]))
