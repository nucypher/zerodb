import persistent
import ZODB
from ZEO import ClientStorage
import zc.zlibstorage
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from repoze.catalog.catalog import Catalog
from BTrees.IOBTree import IOBTree
import BTrees
import transaction
import logging
from pickle import loads
from repoze.catalog.query import Contains
from zope.index.text.lexicon import CaseNormalizer
from zope.index.text.lexicon import Lexicon
from zope.index.text.lexicon import Splitter
from zope.index.text.lexicon import StopWordRemover
from zope.index.text.okapiindex import OkapiIndex
from copy import copy
import time
from zeopermissions import register_auth

register_auth()
logging.basicConfig(level=logging.DEBUG)


class MyIOBTree(IOBTree):
    max_internal_size = 20000
    max_leaf_size = 10000


class MyTreeFamily(BTrees._Family32):
    import mytree as IF


myfamily32 = MyTreeFamily()
myfamily32.IF.family = myfamily32


class MyCatalog(Catalog):
    family = myfamily32


class MyCatalogFieldIndex(CatalogFieldIndex):
    family = myfamily32


class MyCatalogTextIndex(CatalogTextIndex):
    family = myfamily32

    def __init__(self, *args, **kw):
        kw = copy(kw)
        kw["lexicon"] = Lexicon(Splitter(), CaseNormalizer(), StopWordRemover())
        kw["index"] = OkapiIndex(kw["lexicon"], family=myfamily32)
        super(MyCatalogTextIndex, self).__init__(*args, **kw)


class DebugStorage(zc.zlibstorage.ZlibStorage):
    def load(self, oid, version=''):
        data, serial = self.base.load(oid, version)
        obj = self._untransform(data)
        # time.sleep(0.5)
        print oid.encode("hex"), loads(obj), len(data), "->", len(obj)
        return obj, serial


class Page(persistent.Persistent):

    def __init__(self, title="", text=""):
        self.title = title
        self.text = text


def create_objects(root):
    def record_and_index(i, **kw):
        obj = Page(**kw)
        root["pages"][i] = obj
        root["catalog"].index_doc(i, obj)

    for i in range(100):
        record_and_index(i, title="hello %s" % i, text="lorem ipsum dolor sit amet" * 50)
    for i in range(100, 110):
        record_and_index(i, title="hello %s" % i, text="this is something we're looking for" * 50)
    for i in range(110, 200):
        record_and_index(i, title="hello %s" % i, text="lorem ipsum dolor sit amet" * 50)


def make_zodb():
    db = ZODB.DB(DebugStorage(ClientStorage.ClientStorage("/tmp/zeosocket", username="test", password="test", realm="ZEO")))
    conn = db.open()
    root = conn.root()

    with transaction.manager:
        if 'catalog' not in root.keys():
            catalog = MyCatalog()
            catalog["title"] = MyCatalogFieldIndex("title")
            catalog["text"] = MyCatalogTextIndex("text")
            root["catalog"] = catalog

        if 'pages' not in root.keys():
            root["pages"] = MyIOBTree()
            create_objects(root)

    return root


def test_query(root):
    t1 = time.time()
    ids = root['catalog'].query(Contains("text", "something"))
    print "===", time.time() - t1
    return [root["pages"][i] for i in ids[1]]


if __name__ == "__main__":
    root = make_zodb()
    print "==="
    for i in test_query(root):
        print i.title
