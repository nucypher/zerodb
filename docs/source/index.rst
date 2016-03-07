.. ZeroDB documentation master file, created by
   sphinx-quickstart on Sat May 16 10:35:11 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

ZeroDB documentation
====================

Contents:

.. toctree::
   :maxdepth: 2

Overview
========
ZeroDB is an end-to-end encrypted database. It is based on
`ZODB <http://en.wikipedia.org/wiki/Zope_Object_Database>`_ and written in
`Python <https://www.python.org/>`_.

In ZeroDB, the client is responsible for the database logic. Data encryption,
decryption, and compression also happen client side. Therefore, the server
never has any knowledge about the data, its structure, or its order.

Clients also have an adjustable cache which stores the most used parts of data
structures and greatly speeds up queries even when its size is small (e.g. 1
megabyte).

From a developer's perspective, ZeroDB's design is greatly inspired by the `Django
<https://djangoproject.com>`_ ORM and `SQLAlchemy
<http://www.sqlalchemy.org/>`_.

Installation
============
We supply ZeroDB as a Python Package ``zerodb-0.97``, installable via ``pip``.

To run the server and test scripts, clone the ``zerodb-server`` repository,
navigate to the resulting directory and (optionally) create a virtual environment::

    virtualenv .demo

This creates a fresh virtual environment in the directory ``.demo``, which you can
activate using::

    source .demo/bin/activate

Navigate to the ``demo`` directory and install the necessary packages::

    pip install -r requirements.txt


Starting the ZeroDB server and creating users
=============================================
In the ``zerodbext/server`` directory, we supply Python scripts to run a server and
manage users.

    | api.py
    | manage.py
    | run.py

Initializing and Running the ZeroDB server
------------------------------------------

When you ran ``pip install`` previously, the following console scripts were created::

    zerodb-server
    zerodb-manage
    zerodb-api

These map to the files in the ``zerodbext/server`` directory.

So, to initialize a database, just run ``zerodb-manage init_db``.
Enter your username (``root`` by default) and passphrase.

This will create the appropriate database file structure and config file
``authdb.conf`` located in the ``demo/conf`` directory. The default administrator
user can create and remove other users or change their public keys.
However, it doesn't know any other user's private keys.

Run ``zerodb-server`` and you'll get the ZeroDB server running on the host specified
in the file ``demo/conf/server.zcml``.

Healthy output of the running server appears as follows::

    ------
    2015-05-16T16:01:53 INFO ZEO.runzeo (6580) opening storage '1' using FileStorage
    ------
    2015-05-16T16:01:53 INFO ZEO.StorageServer StorageServer created RW with
    storages: 1:RW:db/db.fs
    ------
    2015-05-16T16:01:53 INFO ZEO.StorageServer StorageServer: using auth protocol:
    ecc_auth
    ------
    2015-05-16T16:01:53 INFO ZEO.zrpc (6580) listening on ('localhost', 8001)

Adding more users
-----------------

Instead of being stored in config files, users are normally stored in a
database. In order to manage these users start the zerodb server and open the
admin console::

    zerodb-manage console

This will launch an ipython terminal where you can manage users::

    In [1]: useradd("jamesbond", "secure password")
    In [2]: chpass("jamesbond", "even more secure password")
    In [3]: userdel("jamesbond")

The users you create this way are not administrators and they cannot
manage other users.

Press ``Ctrl+D`` to exit the ipython terminal when you're done.


Using ZeroDB in Python
======================

Unlike many NoSQL databases, you still define data models in ZeroDB. However,
these are only for indexing, and they are dynamically typed. All the fields you
define in the data models are indexed, but objects which you store in the database
can contain any fields you want (they just won't be indexed).

Let's start by writing a data model in ``demo/models.py`` first:

.. literalinclude:: ../../../zerodb-server/demo/models.py

Let's assume the database server we started before is still running. The simplest example
which creates records for us would look like this::

    import transaction
    import zerodb
    import models

    db = zerodb.DB(("localhost", 8001), username="root", password="<your passphrase>")
    e = models.Employee(name="John", surname="Smith", salary=150000,
                        description="Coding power")
    db.add(e)
    transaction.commit()

Now, let's do something more advanced and populate the database with random
data using the script ``create.py``:

.. literalinclude:: ../../../zerodb-server/demo/create.py

Let's play with that data in the Python terminal (or you can write your own
script). We'll need to import ``zerodb`` and query operators from
``zerodb.query`` (same syntax as in `repoze
<http://docs.repoze.org/catalog/usage.html#comparators>`_)::

    >>> import zerodb
    >>> from zerodb.query import *

And we also import our data models::

    >>> from models import *

Let's connect to the database now::

    >>> PASSWORD = "very insecure passphrase - never use it"
    >>> db = zerodb.DB(("localhost", 8001), username="root", password=PASSWORD)

Number of Employees in the database can be determined by just ``len``::

    >>> len(db[Employee])
    10001

Let's try a range query. Here we search for the name *John* and select three of
the matching items::

    >>> db[Employee].query(name="John", limit=3)
    [<John Aquirre who earns $147944>, <John Gauthier who earns $169040>, <John
    Hefner who earns $25895>]

Now, let's do another range query and select all *Johns* who have a salary within
a certain range::

    >>> rich_johns = db[Employee].query(InRange("salary", 195000, 200000),
    name="John")
    >>> len(rich_johns)
    5

We can also do full-text search::

    >>> from_uk = db[Employee].query(Contains("description", "United Kingdom"))
    >>> from_uk
    [<Stephen Hawking who earns $400000>]
    >>> print from_uk[0].description
    A theoretical physicist, cosmologist,
    author and Director of Research at the Centre for
    Theoretical Cosmology within the University of Cambridge,
    Stephen William Hawking resides in the United Kingdom.

Let's remove the record from the last example. We'll need the ``transaction``
module for that::

    >>> import transaction
    >>> db.remove(from_uk[0])
    >>> transaction.commit()
    >>> len(db[Employee])
    10000

Supported Queries
======================
The following comparators can be executed in ZeroDB. Please note that not all of these
have been optimized/tested for performance yet.

Contains(index_name, value)
    Contains query.

Eq(index_name, value)
    Equals query.

NotEq(index_name, value)
    Not equal query.

Gt(index_name, value)
    Greater than query.

Lt(index_name, value)
    Less than query.

Ge(index_name, value)
    Greater (or equal) query.

Le(index_name, value)
    Less (or equal) query.

DoesNotContain(index_name, value)
    Does not contain query

Any(index_name, value)
    Any of query.

NotAny(index_name, value)
    Not any of query (ie, None of query)

All(index_name, value)
    All query.

NotAll(index_name, value)
    NotAll query.

InRange(index_name, start, end, start_exclusive=False, end_exclusive=False)
    Index value falls within a range.

NotInRange(index_name, start, end, start_exclusive=False, end_exclusive=False)
    Index value falls outside a range.

JSON API
======================
To start the api server, make sure you’ve activated the virtual environment and the ZeroDB server is running.
Navigate to the `api_server` directory, and run `python api_server.py`.

Query examples (similar to http://docs.mongodb.org/manual/reference/operator/query/)::

    {"$and": [{"field1": {"$gt": 10}}, {"field2": {"$text": "hello"}}]}
    {field: {"$range": [1, 10]}}

logical_operators
-----------------
"$and": And
    Joins query clauses with a logical AND returns all documents that match the conditions of both clauses.

"$or": Or
    Joins query clauses with a logical OR returns all documents that match the conditions of either clause.

"$not": Not
    Inverts the effect of a query expression and returns documents that do not match the query expression.

field_operators
---------------
"$eq": Eq
    Matches values that are equal to a specified value.

"$ne": NotEq
    Matches all values that are not equal to a specified value.

"$lt": Lt
    Matches values that are less than a specified value.

"$lte": Le
    Matches values that are less than or equal to a specified value.

"$gt": Gt
    Matches values that are greater than a specified value.

"$gte": Ge
    Matches values that are greater than or equal to a specified value.

"$range": InRange
    Matches values that fall within a specified range.
    
"$nrange": NotInRange
    Matches values that do not fall within a specified range.
    
"$text": Contains
    Performs text search for a specified value..

"$ntext": DoesNotContain
    Performs text search for the lack of a specified value.
    
"$in": Any
    Matches any of the values specified in an array.

"$all": All
    Matches arrays that contain all elements specified in the query.

"$nany": NotAny
    Matches none of the values specified in an array.

"$nin": NotAll
    Matches arrays that contain all elements specified in the query.
    

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

