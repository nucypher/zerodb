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
import random


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


class Salary(persistent.Persistent):
    def __init__(self, name="", surname="", salary=0):
        self.name = name
        self.surname = surname
        self.salary = salary


def create_objects(root, count=20000):
    def p_record_and_index(i, **kw):
        obj = Page(**kw)
        root["pages"][i] = obj
        root["pages_catalog"].index_doc(i, obj)

    def s_record_and_index(i, **kw):
        obj = Salary(**kw)
        root["salaries"][i] = obj
        root["salaries_catalog"].index_doc(i, obj)

    for i in range(count / 2):
        p_record_and_index(i, title="hello %s" % i, text="lorem ipsum dolor sit amet" * 50)
    for i in range(count / 2, count / 2 + 10):
        p_record_and_index(i, title="hello %s" % i, text="this is something we're looking for" * 50)
    for i in range(count / 2 + 10, count):
        p_record_and_index(i, title="hello %s" % i, text="lorem ipsum dolor sit amet" * 50)

    for i in range(count):
        s_record_and_index(i, name="John" + str(i), surname="Smith" + str(i), salary=random.randrange(50000, 200000))


def make_zodb():
    db = ZODB.DB(DebugStorage(ClientStorage.ClientStorage("/tmp/zeosocket")))
    conn = db.open()
    root = conn.root()

    if 'pages_catalog' not in root.keys():
        catalog = Catalog()
        catalog["title"] = CatalogFieldIndex("title")
        catalog["text"] = CatalogTextIndex("text")
        root["pages_catalog"] = catalog

    if 'salaries_catalog' not in root.keys():
        catalog = Catalog()
        catalog["name"] = CatalogFieldIndex("name")
        catalog["surname"] = CatalogFieldIndex("surname")
        catalog["salary"] = CatalogFieldIndex("salary")
        root["salaries_catalog"] = catalog

    if 'pages' not in root.keys():
        root["pages"] = family32.IO.BTree()
        root["salaries"] = family32.IO.BTree()
        create_objects(root)

    return root


def test_query_1(root):
    t1 = time.time()
    ids = root['pages_catalog'].query(Contains("text", "something"))
    print "===", time.time() - t1
    return [root["pages"][i] for i in ids[1]]


def test_query_2(root):
    from repoze.catalog.query import Lt, Gt
    return root["salaries_catalog"].query(Gt("salary", 130000) & Lt("salary", 130050))


if __name__ == "__main__":
    root = make_zodb()
    print "==="
    for i in test_query_1(root):
        print i.title
    print "==="

    print test_query_2(root)[1]

    transaction.commit()
