import logging
import transaction
from db import WikiPage

logging.basicConfig(level=logging.DEBUG)

# These will be pretty slow tests: around 2700 wikipedia pages are indexed and added to the DB
# Could take up to a minute


def get_one(db):
    key = db[WikiPage]._objects.tree.keys()[0]
    doc = db[WikiPage]._objects[key]
    return key, doc


def get_cat(db):
    return db[WikiPage]._catalog['text']


def test_indexed(wiki_db):
    # The DB is indexed and loaded
    assert len(wiki_db[WikiPage]) == get_cat(wiki_db).documentCount()


def test_reindex(wiki_db):
    with transaction.manager:
        key, test_doc = get_one(wiki_db)
        test_doc.text += "\nTestWord to change the text."
        get_cat(wiki_db).reindex_doc(key, test_doc)


def test_unindex(wiki_db):
    with transaction.manager:
        key, _ = get_one(wiki_db)
        get_cat(wiki_db).unindex_doc(key)
