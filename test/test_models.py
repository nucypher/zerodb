import pytest
from datetime import datetime
from datetime import timedelta

from zerodb import models
import zerodb
import zerodb.db
from zerodb.models import fields
from zerodb.models.exceptions import ModelException
from db import TEST_PASSPHRASE


class TestMe(models.Model):
    title = fields.Field(index=False)
    content = fields.Text(index=False)
    age = fields.Field(default=0)
    timestamp = fields.Field(default=datetime.utcnow)
    all_text = fields.Text(virtual=lambda o: o.title + " " + o.content)


def test_model_metaclass():
    assert len(TestMe._z_indexed_fields) == 3
    assert len(TestMe._z_required_fields) == 2
    assert len(TestMe._z_default_fields) == 2
    assert TestMe._z_virtual_fields.keys() == ["all_text"]


def test_model():
    test_timestamp = datetime(year=1984, month=1, day=1)
    obj1 = TestMe(title="Hello", content="World", age=5, timestamp=test_timestamp)
    obj2 = TestMe(title="Hello world", content="Lorem ipsum")
    obj3 = TestMe(title="Hello", content="World", extra="something")

    with pytest.raises(ModelException):
        TestMe(title="This is not enough")

    assert obj1.title == "Hello"
    assert obj1.content == "World"
    assert obj1.age == 5
    assert obj1.timestamp == test_timestamp

    assert obj1._z_virtual_fields["all_text"](obj1) == "Hello World"

    assert obj2.title == "Hello world"
    assert obj2.content == "Lorem ipsum"
    assert obj2.age == 0
    assert (datetime.utcnow() - obj2.timestamp) < timedelta(seconds=1)

    assert obj1.title == "Hello"
    assert obj1.content == "World"
    assert obj3.age == 0
    assert (datetime.utcnow() - obj3.timestamp) < timedelta(seconds=1)
    assert obj3.extra == "something"


def test_db(zeo_server):
    db = zerodb.DB(zeo_server, username="root", password=TEST_PASSPHRASE, debug=True)
    assert len(db._models) == 0
    assert isinstance(db[TestMe], zerodb.db.DbModel)
    assert len(db._models) == 1
    assert TestMe in db._models
    db.disconnect()


def test_dbmodel(zeo_server):
    db = zerodb.DB(zeo_server, username="root", password=TEST_PASSPHRASE, debug=True)
    assert db[TestMe]._model == TestMe
    assert db[TestMe]._db == db
    assert db[TestMe]._catalog_name == "catalog__testme"
    assert db[TestMe]._intid_name == "store__testme"
    db.disconnect()
