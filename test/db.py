""" Test database """

import transaction
from zerodb.models import Model
from zerodb.models import fields
import zerodb

TEST_PASSPHRASE = "v3ry 53cr3t pa$$w0rd"


class Page(Model):
    title = fields.Field()
    text = fields.Text()


class Salary(Model):
    name = fields.Field()
    surname = fields.Field()
    salary = fields.Field()
    full_name = fields.Text(virtual=lambda x: x.name + " " + x.surname)
    future_salary = fields.Field(virtual=lambda x: x.salary * 2)


def create_objects_and_close(sock, count=200):
    db = zerodb.DB(sock, username="root", password=TEST_PASSPHRASE, debug=True)
    with transaction.manager:
        for i in range(count / 2) + range(count / 2 + 10, count):
            db.add(Page(title="hello %s" % i, text="lorem ipsum dolor sit amet" * 50))
        for i in range(count / 2, count / 2 + 10):
            db.add(Page(title="hello %s" % i, text="this is something we're looking for" * 50))
        for i in range(count):
            db.add(Salary(
                name="John-%s" % i,
                surname="Smith-%i" % i,
                salary=50000 + (200000 - 50000) * i / (count - 1)))
        db.add(Salary(
            name="Hello",
            surname="World",
            salary=1000000))
        db.add(Page(title="one two",
            text='"The quick brown fox jumps over a lazy dog" is an English-language pangram - a phrase that contains all of the letters of the alphabet.'))
    db.disconnect()
