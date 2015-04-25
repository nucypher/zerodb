""" Test database """

import transaction
from zerodb.models import Model
from zerodb.models import fields
import zerodb
from zerodb.crypto import AES

PASSPHRASE = "very very secret password"


class Page(Model):
    title = fields.Field()
    text = fields.Text()


class Salary(Model):
    name = fields.Field()
    surname = fields.Field()
    salary = fields.Field()


def create_objects_and_close(sock, count=200):
    db = zerodb.DB(sock, cipher=AES(passphrase=PASSPHRASE), debug=True)
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
    db.disconnect()
