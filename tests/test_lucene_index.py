import logging
import pytest
import transaction
import zerodb
from zerodb.query import Contains

from zerodb.testing import TEST_PASSPHRASE, do_zeo_server
from db import Page, WikiPage

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(scope="module")
def many_server(request, pass_file, tempdir):
    sock = do_zeo_server(request, pass_file, tempdir, name="many_server")
    db = zerodb.DB(sock, username="root", password=TEST_PASSPHRASE, debug=True)
    with transaction.manager:
        for i in range(2000):
            db.add(Page(title="hello %s" % i, text="lorem ipsum dolor sit amet" * 2))
        for i in range(1000):
            # Variable length while keeping number of terms the same
            # will cause variable scores
            db.add(Page(title="hello %s" % i, text="this is something we're looking for" * int(i ** 0.5)))
        db.add(Page(title="extra page", text="something else is here"))
    db.disconnect()
    return sock


@pytest.fixture(scope="module")
def many_db(request, many_server):
    zdb = zerodb.DB(many_server, username="root", password=TEST_PASSPHRASE, debug=True)

    @request.addfinalizer
    def fin():
        zdb.disconnect()  # I suppose, it's not really required

    return zdb


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
        original_size = len(test_doc.text)
        test_doc.text += "\nTestWord to change the text."
        get_cat(wiki_db).reindex_doc(key, test_doc)

    with transaction.manager:
        test_doc = wiki_db[WikiPage]._objects[key]
        test_doc.text = test_doc.text[:original_size] + "\nNewTestWord to change the text."
        get_cat(wiki_db).reindex_doc(key, test_doc)


def test_unindex(wiki_db):
    with transaction.manager:
        cat = get_cat(wiki_db)
        key, _ = get_one(wiki_db)
        cat.unindex_doc(key)
        cat.unindex_doc(-99)  # No such ID, should be OK


def test_idf2(wiki_db):
    with transaction.manager:
        text = "Africa Asia NonExistingWord"
        index = get_cat(wiki_db).index
        wids = index._lexicon.sourceToWordIds(text)
        assert len(wids) == 3
        wids = index._remove_oov_wids(wids)
        assert len(list(wids)) == 2
        idfs = map(index.idf2, wids)
        assert all(idf > 0 for idf in idfs)


def test_query_weight(wiki_db):
    index = get_cat(wiki_db).index
    qs = "Africa Asia SomethingWhichIsNotThere"
    assert index.query_weight(qs) > 0
    assert index.query_weight(index._lexicon.termToWordIds(qs.split())) == index.query_weight(qs)


def test_search_wids(wiki_db):
    index = get_cat(wiki_db).index
    text = "Africa Asia"
    wids = index._lexicon.sourceToWordIds(text)
    for wordinfo, idf in index._search_wids(wids):
        assert idf > 0
        weight, docid = next(iter(wordinfo))
        assert weight < 0
        assert docid >= 0


def test_search(wiki_db):
    index = get_cat(wiki_db).index
    assert list(index.search("")) == []
    assert len(list(index.search("Africa"))) > 0
    assert len(list(index.search("Australia rugby"))) > 0
    assert len(list(index.search_glob("Austral*"))) > 0
    assert len(list(index.search_glob("itisnotthere*"))) == 0


def test_search_many(many_db):
    index = many_db[Page]._catalog["text"].index
    it = index.search("something looking")
    ids = [x[0] for x in it]
    assert len(ids) == 1000
    # Longer docs for this query and our synthetic docs have higher score
    lens = [len(many_db[Page]._objects[i].text) for i in ids]
    assert lens == sorted(lens, reverse=True)


def test_search_query(many_db, wiki_db):
    # High level search using .query interface
    pages = many_db[Page].query(Contains("text", "something looking"))
    assert len(pages) == 1000
    lens = [len(page.text) for page in pages]
    assert lens == sorted(lens, reverse=True)

    assert len(wiki_db[WikiPage].query(text="Austra* rugb?")) > 0
    assert len(wiki_db[WikiPage].query(text="Austra* rugb?", title="Geoff Toovey")) > 0
