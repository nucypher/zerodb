""" Test database """

import random
import transaction

from os.path import abspath, join, dirname
from zerodb.models import Model
from zerodb.models import fields
import zerodb

import wiki

from zerodb.testing import TEST_PASSPHRASE


class Page(Model):
    title = fields.Field()
    text = fields.Text()


# This is to test foreign relationships and, importantly, backrefs as well
# This class if for one-to-many (1 department -> many salaries)
# and salary -> department
#
# What do we need to do for that:
# * indexing weakrefs
# * having a field which is a collection of objects, e.g.:
#       department.salaries.add(salary_object) where salaries is catalog
#           that said, if catalog is too heavy (Salary example):
#               * pickle: 1219 (zlib 668)
#               * json: 3382 (zlib 504)
#               * msgpack: 2658 (zlib 528)
#       department_salaries can be a many-to-many connector
# * and we need some tracking of relationships consistency (hello NoSQL)
class Department(Model):
    name = fields.Text()
    # TODO Need to make a backref to Salary
    # in order to reindex once Department is changed


class Salary(Model):
    name = fields.Field()
    surname = fields.Field()
    salary = fields.Field()
    full_name = fields.Text(virtual=lambda x: x.name + " " + x.surname)
    future_salary = fields.Field(virtual=lambda x: x.salary * 2)

    # Foreign relationships
    department_name = fields.Field(virtual=lambda o: o.department.name)  # Enable looking up Salary by department
    department_id = fields.Field(virtual=lambda o: o.department._p_uid)  # Department ID


def create_objects_and_close(sock, count=200, dbclass=zerodb.DB):
    db = dbclass(sock, username="root", password=TEST_PASSPHRASE, debug=True)
    with transaction.manager:
        # Initialize departments
        departments = [Department(name="Mobile"), Department(name="Web"), Department(name="Tools"),
                       Department(name="Money"), Department(name="Human Resources")]
        db.add(departments)

    with transaction.manager:
        for i in list(range(count // 2)) + list(range(count // 2 + 10, count)):
            db.add(Page(title="hello %s" % i, text="lorem ipsum dolor sit amet" * 50))
        for i in range(count // 2, count // 2 + 10):
            db.add(Page(title="hello %s" % i, text="this is something we're looking for" * 50))
        for i in range(count):
            db.add(Salary(
                name="John-%s" % i,
                surname="Smith-%i" % i,
                salary=50000 + (200000 - 50000) * i / (count - 1),
                department=random.choice(departments)))
        db.add(Salary(
            name="Hello",
            surname="World",
            salary=1000000,
            department=random.choice(departments)))
        db.add(Page(
            title="one two",
            text='"The quick brown fox jumps over a lazy dog" is an English-language pangram - a phrase that contains all of the letters of the alphabet.'))
    db.disconnect()


class WikiPage(Model):
    id = fields.Field()
    title = fields.Field()
    text = fields.Text()


def add_wiki_and_close(sock, count=200, dbclass=zerodb.DB):
    db = dbclass(sock, username="root", password=TEST_PASSPHRASE, debug=True)
    with transaction.manager:
        for doc in wiki.read_docs(join(dirname(abspath(__file__)), "wiki_sample")):
            p = WikiPage(**doc)
            db.add(p)
    db.disconnect()
