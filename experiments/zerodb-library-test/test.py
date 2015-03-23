import persistent
import ZODB
from ZEO import ClientStorage
import zc.zlibstorage
import transaction
import logging
from pickle import loads
from repoze.catalog.query import Contains
import time
from zerodb.catalog import Catalog, CatalogTextIndex, CatalogFieldIndex
from zerodb.trees import family32


logging.basicConfig(level=logging.DEBUG)


class DebugStorage(zc.zlibstorage.ZlibStorage):
    def load(self, oid, version=''):
        data, serial = self.base.load(oid, version)
        obj = self._untransform(data)
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

    for i in range(10000):
        record_and_index(i, title="hello %s" % i, text="lorem ipsum dolor sit amet" * 50)
    for i in range(10000, 10010):
        record_and_index(i, title="hello %s" % i, text="this is something we're looking for" * 50)
    for i in range(10010, 20000):
        record_and_index(i, title="hello %s" % i, text="lorem ipsum dolor sit amet" * 50)


def make_zodb():
    db = ZODB.DB(DebugStorage(ClientStorage.ClientStorage("/tmp/zeosocket")))
    conn = db.open()
    root = conn.root()

    if 'catalog' not in root.keys():
        catalog = Catalog()
        catalog["title"] = CatalogFieldIndex("title")
        catalog["text"] = CatalogTextIndex("text")
        root["catalog"] = catalog

    if 'pages' not in root.keys():
        root["pages"] = family32.IO.BTree()
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
    print "==="
    t1 = time.time()

    obj = Page(title="blah-blah", text="Blah blah 5" * 50)
    root["pages"][20001] = obj
    root["catalog"].index_doc(20001, obj)
    print "===", time.time() - t1

    transaction.commit()
