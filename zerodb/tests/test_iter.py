import itertools
import pytest
import six
from six.moves import map as imap

from zerodb.util.iter import Sliceable
from zerodb.catalog.query import Gt
from db import Salary


def test_sliceable():
    it = Sliceable(lambda: imap(str, itertools.count()))
    assert it[500] == "500"
    assert it[505] == "505"
    it1 = it.iterator
    it.cache.clear()
    assert it[0] == "0"
    assert it[2] == "2"
    assert it1 is not it.iterator

    assert it[10:15:3] == [str(i) for i in range(10, 15, 3)]
    assert it[101:200:5] == [str(i) for i in range(101, 200, 5)]
    assert it[20:25:3] == [str(i) for i in range(20, 25, 3)]

    assert it[5:100] == [str(i) for i in range(5, 100)]
    it1 = it.iterator
    assert it[10:20] == [str(i) for i in range(10, 20)]
    assert it.iterator is it1

    with pytest.raises(KeyError):
        it[-1]
    with pytest.raises(KeyError):
        it["raise"]

    it = Sliceable(lambda: six.moves.xrange(10))

    assert len([i for i in it]) == 10
    assert len(it) == 10

    it = Sliceable(lambda: imap(str, six.moves.xrange(100)))
    assert len(it) == 100
    it = Sliceable(lambda: imap(str, six.moves.xrange(100)))
    assert it[10:] == [str(i) for i in range(10, 100)]


def test_dictify(db):
    test_salaries = db[Salary].query(Gt("salary", 100000)).dictify()
    obj = next(test_salaries)
    assert set(obj.keys()) == set(["name", "surname", "salary", "department"])
