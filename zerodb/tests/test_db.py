import logging
import mock
import transaction
from itertools import islice
from db import Page, Salary, Department
from zerodb.catalog.query import Contains, InRange, Eq, Gt
# Also need to test optimize, Lt(e), Gt(e)

logging.basicConfig(level=logging.DEBUG)


def test_query(db):
    pre_request_count = db._storage._debug_download_count
    assert len(db[Page]) == 201
    assert len(db[Salary]) == 201
    test_pages = db[Page].query(Contains("text", "something"))
    pre_range_count = db._storage._debug_download_count
    assert pre_range_count - pre_request_count < 15  # We'll have performance testing separately this way
    assert len(test_pages) == 10

    test_salaries_1 = db[Salary].query(InRange("salary", 130000, 180000), sort_index="salary", limit=2)
    test_salaries_2 = db[Salary].query(InRange("salary", 130000, 130001), sort_index="salary", limit=2)
    post_range_count = db._storage._debug_download_count
    assert len(test_salaries_1) == 2
    assert len(test_salaries_2) == 0
    for s in test_salaries_1:
        assert s.salary >= 130000
        assert s.salary <= 180000
    # Check that we pre-downloaded all objects into cache
    assert db._storage._debug_download_count - post_range_count <= 5

    million_employee = db[Salary].query(salary=1000000)
    assert len(million_employee) == 1
    assert million_employee[0].name == "Hello"

    assert len(db[Salary].query(full_name="Hello World")) == 1
    assert len(db[Salary].query(full_name="Hell? Wor*")) == 1
    assert db[Salary].query(Contains("full_name", "Hello"))[0] == million_employee[0]

    assert db[Salary].query(future_salary=2000000)[0] == million_employee[0]

    assert len(db[Salary].query(department_name="Mobile")) > 0
    department = db[Department].query(name="Money")[0]
    assert len(db[Salary].query(department_id=department._p_uid)) > 0

    test_pages = db[Page].query(Contains("text", "something"))[:5]
    assert len(test_pages) == 5

    db[Salary].query(InRange("salary", 130000, 180000), name="John-2")
    db[Salary].query(InRange("salary", 130000, 180000) | Eq("name", "John-2"))

    # test Length object
    delattr(db[Salary]._objects, "length")
    assert len(db[Salary]) > 0
    assert db[Salary]._objects.length.value == len(db[Salary])


def test_add(db):
    with transaction.manager:
        pre_commit_count = db._storage._debug_download_count
        page = Page(title="hello", text="Quick brown lazy fox jumps over lorem  ipsum dolor sit amet")
        db.add(page)
        post_commit_count = db._storage._debug_download_count
    print("Number of requests:", post_commit_count - pre_commit_count)
    assert post_commit_count - pre_commit_count < 22

    with transaction.manager:
        db.remove(page)


def test_reindex(db):
    with transaction.manager:
        page = Page(title="hello", text="Quick0 brown lazy fox jumps over lorem  ipsum dolor sit amet")
        docid = db.add(page)
    assert len(db[Page].query(Contains("text", "quick0"))) == 1

    # DbModel, by ID
    with transaction.manager:
        page.text = "Quick1 brown lazy fox jumps over well, you know"
        db[Page].reindex(docid)
    assert len(db[Page].query(Contains("text", "quick0"))) == 0
    assert len(db[Page].query(Contains("text", "quick1"))) == 1

    # DbModel, by obj
    with transaction.manager:
        page.text = "quick2 brown lazy fox jumps over well, you know"
        db[Page].reindex(page)
    assert len(db[Page].query(Contains("text", "quick1"))) == 0
    assert len(db[Page].query(Contains("text", "quick2"))) == 1

    # DB, by obj
    with transaction.manager:
        page.text = "quick3 brown lazy fox jumps over well, you know"
        db[Page].reindex(page)
    assert len(db[Page].query(Contains("text", "quick2"))) == 0
    assert len(db[Page].query(Contains("text", "quick3"))) == 1

    # DB, multiple objects
    with transaction.manager:
        page2 = Page(title="hello", text="Quick4 brown lazy fox jumps over lorem  ipsum dolor sit amet")
        db.add(page2)

    with transaction.manager:
        page.text = "quick5 brown lazy fox jumps over well, you know"
        page2.text = "quick5 brown lazy fox jumps over well, you know"
        db.reindex([page, page2])
    assert len(db[Page].query(Contains("text", "quick3") | Contains("text", "quick4"))) == 0
    assert len(db[Page].query(Contains("text", "quick5"))) == 2


def test_auto_reindex(db):
    with transaction.manager:
        page = Page(title="hello", text="autoreindex0, test whether to work")
        db.add(page)
    assert len(db[Page].query(Contains("text", "autoreindex0"))) == 1

    with transaction.manager:
        page.text = "autoreindex1, test whether to work"
    assert len(db[Page].query(Contains("text", "autoreindex0"))) == 0
    assert len(db[Page].query(Contains("text", "autoreindex1"))) == 1

    with transaction.manager:
        page2 = Page(title="hello", text="autoreindex2, test whether to work")
        db.add(page2)

    with transaction.manager:
        page.text = "autoreindex3, test whether to work"
        page2.text = "autoreindex3, test whether to work"
    assert len(db[Page].query(Contains("text", "autoreindex1") | Contains("text", "autoreindex2"))) == 0
    assert len(db[Page].query(Contains("text", "autoreindex3"))) == 2

    with mock.patch("zerodb.db.DbModel.reindex_one") as reindex_mock:
        with transaction.manager:
            page.text = "autoreindex3, test whether to work1"
            page.text = "autoreindex3, test whether to work2"
            page.text = "autoreindex3, test whether to work3"
        assert reindex_mock.call_count == 1

    db.enableAutoReindex(False)
    with transaction.manager:
        page.text = "autoreindex4, test whether to work"
    assert len(db[Page].query(Contains("text", "autoreindex3"))) == 2
    assert len(db[Page].query(Contains("text", "autoreindex4"))) == 0

    db.enableAutoReindex(True)
    with transaction.manager:    # should not throw ModleException
        page3 = Page(title="helloworld", text="autoreindex5, test whether to work")
        page3.title = "helloworld1"
    assert len(db[Page].query(Eq("title", "helloworld"))) == 0
    assert len(db[Page].query(Eq("title", "helloworld1"))) == 0

    with mock.patch("zerodb.db.DbModel.reindex_one") as reindex_mock:
        with transaction.manager:  # should not reindex
            page3 = Page(title="helloworld", text="autoreindex5, test whether to work")
            page3.title = "helloworld1"
            db.add(page3)
        assert reindex_mock.call_count == 0

    with transaction.manager:  # should  reindex
        page3 = Page(title="helloworld", text="autoreindex6, test whether to work")
        db.add(page3)
        page3.title = "helloworld1"
        page3.text = "autoreindex7, test whether to work"
    assert len(db[Page].query(Eq("title", "helloworld"))) == 0
    assert len(db[Page].query(Eq("title", "helloworld1"))) == 2
    assert len(db[Page].query(Contains("text", "autoreindex6"))) == 0
    assert len(db[Page].query(Contains("text", "autoreindex7"))) == 1

    with mock.patch("zerodb.db.DbModel.reindex_one") as reindex_mock:
        with transaction.manager:  # should  reindex
            page3 = Page(title="helloworld", text="autoreindex6, test whether to work")
            db.add(page3)
            page3.title = "helloworld1"
            page3.text = "autoreindex7, test whether to work"
        assert reindex_mock.call_count == 1


def test_fieldindex_typechange(db):
    with transaction.manager:
        for i in range(30):
            db.add(Salary(
                name="Tom",
                surname="Jackson-%s" % i,
                salary=10000 + 100 * i))
    test1 = db[Salary].query(InRange("salary", 9999, 14000))
    assert len(test1) == 30
    test2 = db[Salary].query(InRange("salary", 9999, 10901) & Eq("name", "Tom"))
    assert len(test2) == 10


def test_repr(db):
    data = db[Salary].query(Gt("salary", 100000))
    s = str(data)
    assert s.startswith("[")
    assert "..." in s
    assert s.endswith("]")
    lines = s.split("\n")
    assert sum([l.endswith(",") for l in lines]) == 5
    assert sum([l.startswith(" ") for l in lines]) == 5

    data = db[Salary].query(Gt("salary", 100000), name="Nonexistent")
    assert str(data) == "[]"


def test_pack(db):
    db.pack()
    assert len(db[Page]) > 0


def test_all_uid(db):
    # Test for https://gist.github.com/micxjo/a097698b33fc4669b0b4
    page = Page(title="Test page", text="Hello world")
    with transaction.manager:
        db.add(page)

    del page
    # Clear in-memory and on-disk caches
    db._storage._cache.clear()
    db._connection._cache.full_sweep()

    for item in db[Page].all():
        assert hasattr(item, "_p_uid")
        del item

    db._storage._cache.clear()
    db._connection._cache.full_sweep()

    for uid in db[Page].all_uids():
        obj = db[Page][uid]
        assert hasattr(obj, "_p_uid")
        del obj

    db._storage._cache.clear()
    db._connection._cache.full_sweep()

    uids = list(islice(db[Page].all_uids(), 10))
    objs = db[Page][uids]
    for obj in objs:
        assert hasattr(obj, "_p_uid")

    objs = list(db[Page].all())
    obj = objs[0]
    obj._p_activate()
    assert hasattr(obj, "_p_uid")

    objs[1].text += " xxx"
    transaction.commit()
    for obj in objs:
        assert hasattr(obj, "_p_uid")
