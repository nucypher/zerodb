import persistent
import ZODB
from ZODB import FileStorage
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
import read_lkml

logging.basicConfig(level=logging.DEBUG)

DEBUG = True


class MyIOBTree(IOBTree):
    max_internal_size = 100000
    max_leaf_size = 50000


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
        if DEBUG:
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

    i = 0
    for title, text in read_lkml.all():
        if title and text:
            record_and_index(i, title=title, text=text)
            # record_and_index(i, title=unicode(title.decode("iso8859-1")), text=unicode(text.decode("iso8859-1")))
            i += 1


def make_zodb():
    # db = ZODB.DB(DebugStorage(FileStorage.FileStorage("db/my.fs")))
    # db = ZODB.DB(DebugStorage(ClientStorage.ClientStorage("/tmp/zeosocket")))
    db = ZODB.DB(DebugStorage(ClientStorage.ClientStorage(("ec2-52-10-86-231.us-west-2.compute.amazonaws.com", 3000))))
    conn = db.open()
    root = conn.root()

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
    ids = root['catalog'].query(Contains("text", "linus and torvalds and hans"))
    print "===", time.time() - t1
    return [root["pages"][i] for i in ids[1]]

def query(root, field, *args):
    ids = root["catalog"].query(*args)
    return [root[field][i] for i in ids[1]]

if __name__ == "__main__":
    root = make_zodb()
    print "==="
    for i in test_query(root):
        print i.title
    print "==="

    transaction.commit()
