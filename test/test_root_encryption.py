from zope.component import getGlobalSiteManager
from zerodb.transform.interfaces import IEncrypter
from zerodb.transform.encrypt_common import get_encryption_signature


def test_root_encryption(db):
    _gsm = getGlobalSiteManager()
    utility = _gsm.getUtility(IEncrypter)
    edata, _ = db._connection._storage.base.load(db._connection._db._root_oid)
    assert get_encryption_signature(edata) == utility.name
    for obj in db._root.values():
        edata, _ = db._connection._storage.base.load(obj._p_oid)
        assert get_encryption_signature(edata) == b""
