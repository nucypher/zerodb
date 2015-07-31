import logging
import transaction
from db import Page, Salary, Department
from zerodb.catalog.query import Contains, InRange
# Also need to test optimize, Lt(e), Gt(e)

logging.basicConfig(level=logging.DEBUG)


def test_query(db):
    pre_request_count = db._storage._debug_download_count
    assert len(db[Page]) == 201
    assert len(db[Salary]) == 201
    test_pages = db[Page].query(Contains("text", "something"))
    pre_range_count = db._storage._debug_download_count
    assert pre_range_count - pre_request_count < 20  # We'll have performance testing separately this way
    test_salaries_1 = db[Salary].query(InRange("salary", 130000, 180000), sort_index="salary", limit=2)
    test_salaries_2 = db[Salary].query(InRange("salary", 130000, 130001), sort_index="salary", limit=2)
    post_range_count = db._storage._debug_download_count
    assert len(test_pages) == 10
    assert len(test_salaries_1) == 2
    assert len(test_salaries_2) == 0
    for s in test_salaries_1:
        assert s.salary >= 130000
        assert s.salary <= 180000
    # Check that we pre-downloaded all objects into cache
    assert db._storage._debug_download_count == post_range_count

    million_employee = db[Salary].query(salary=1000000)
    assert len(million_employee) == 1
    assert million_employee[0].name == "Hello"

    assert len(db[Salary].query(full_name="Hello World")) == 1
    assert len(db[Salary].query(full_name="Hell? Wor*")) == 1
    assert db[Salary].query(Contains("full_name", "Hello"))[0] == million_employee[0]

    assert db[Salary].query(future_salary=2000000)[0] == million_employee[0]

    assert len(db[Salary].query(department_name="Mobile")) > 0
    department = db[Department].query(name="Money")[0]
    assert len(db[Salary].query(department_id=department._v_uid)) > 0


def test_add(db):
    with transaction.manager:
        pre_commit_count = db._storage._debug_download_count
        page = Page(title="hello", text="Quick brown lazy fox jumps over lorem  ipsum dolor sit amet")
        db.add(page)
        post_commit_count = db._storage._debug_download_count
    print "Number of requests:", post_commit_count - pre_commit_count
    assert post_commit_count - pre_commit_count < 22

    with transaction.manager:
        db.remove(page)
