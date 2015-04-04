import pytest
from zerodb import models
from zerodb.models import fields
from zerodb.models.exceptions import ModelException
from datetime import datetime
from datetime import timedelta


def test_model():
    class TestMe(models.Model):
        title = fields.Field()
        content = fields.Text()
        age = fields.Field(default=0)
        timestamp = fields.Field(default=datetime.utcnow)

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

    assert obj2.title == "Hello world"
    assert obj2.content == "Lorem ipsum"
    assert obj2.age == 0
    assert (datetime.utcnow() - obj2.timestamp) < timedelta(seconds=1)

    assert obj1.title == "Hello"
    assert obj1.content == "World"
    assert obj3.age == 0
    assert (datetime.utcnow() - obj3.timestamp) < timedelta(seconds=1)
    assert obj3.extra == "something"
