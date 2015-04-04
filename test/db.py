""" Test database """

import persistent
import ZODB
import transaction
from repoze.catalog.query import Contains
import time
from zerodb.catalog import Catalog, CatalogTextIndex, CatalogFieldIndex
from zerodb.trees import family32
import random
import logging
from zerodb.storage import client_storage


class Page(persistent.Persistent):

    def __init__(self, title="", text=""):
        self.title = title
        self.text = text


class Salary(persistent.Persistent):
    def __init__(self, name="", surname="", salary=0):
        self.name = name
        self.surname = surname
        self.salary = salary


def create_objects(root, count=200):
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


def get_storage(sock):
    return client_storage(sock)


def get_zodb(sock):
    db = ZODB.DB(get_storage(sock))
    conn = db.open()
    root = conn.root()

    return root


def create_objects_and_close(sock):
    logging.debug("Creating test objects")
    db = ZODB.DB(get_storage(sock))
    conn = db.open()
    root = conn.root()
    create_objects(root)
    transaction.commit()
    conn.close()


def test_query_1(root):
    t1 = time.time()
    ids = root['pages_catalog'].query(Contains("text", "something"), sort_index="title", limit=2)
    print "===", time.time() - t1
    return [root["pages"][i] for i in ids[1]]


def test_query_2(root):
    from repoze.catalog.query import InRange
    # return root["salaries_catalog"].query(Gt("salary", 130000) & Lt("salary", 130050))
    # logical multiplication of two conditions is totally ineffective, apparently
    # E.g. handled totally out of db (so, that needs some work, obviously!)
    return root["salaries_catalog"].query(InRange("salary", 130000, 130050), sort_index="salary", limit=2)
