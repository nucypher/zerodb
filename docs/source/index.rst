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
`Python <https://www.python.org/>`_ (with some compiled C extensions).

In ZeroDB, the client is responsible for the database logic. Data encryption,
decryption, and compression also happen client side. Therefore, the server
never has any knowledge about the data, its structure, or its order.

Clients also have an adjustable cache which stores the most-used parts of data
structures and greatly speeds up queries even when its size is small (e.g. 1
megabyte).

From a developer's perspective, ZeroDB's design is greatly inspired by the
`Django <https://djangoproject.com>`_ ORM and 
`SQLAlchemy <http://www.sqlalchemy.org/>`_.

Installation
============

We supply ZeroDB as a Python Package ``zerodb``, installable via ``pip``.
Starting at version 0.99, zerodb asyncio and, hence, requires Python 3.5.

Dependencies
-------------
Firstly, you need Python 3.5. If you are using OS X or Windows, check
`Official Python website <https://www.python.org>`_.
If you are using Ubuntu with version earlier than 16.04, you may find useful
`Deadsnakes PPA <https://launchpad.net/~fkrull/+archive/ubuntu/deadsnakes>`_.

Next, you need to make sure you have pip installed, as well as some dev headers
and compilers. In Ubuntu::

    $ sudo apt-get install python3-pip build-essential \
                           python3-dev libffi-dev libssl-dev

On some systems you may also need to install ``libzmq-dev`` to get IPython
working properly.
With this, you have necessary dependencies. If you want to install only client
library globally in your system (convenient in Docker images or AWS
instances)::

    $ sudo pip3 install zerodb==0.99.0a3

If you want to install the server, you can also do::

    $ sudo pip3 install zerodb-server==0.2.0a2

If you install everything on your local machine, you may want to do so in
virtualenv instead. So, for zerodb server::

    $ sudo pip3 install virtualenv
    $ virtualenv -p python3.5 server_env
    $ source server_env/bin/activate
    $ pip3 install zerodb-server==0.2.0a2

Demo files
------------

You can find demo files in `zerodb-server git repository <https://github.com/zerodb/zerodb-server/>`_::

    $ git clone https://github.com/zerodb/zerodb-server.git
    $ cd zerodb-server/demo

Optionally, create a virtual environment::

    $ virtualenv -p python3.5 .demo

This creates a fresh virtual environment in the directory ``.demo``,
which you can activate using::

    $ source .demo/bin/activate

Install packages necessary for the demo::

    $ pip3 install -r requirements.txt


Starting the ZeroDB server and creating users
=============================================

Initializing and Running the ZeroDB server
------------------------------------------

When you ran ``pip3 install`` previously, the following console scripts were created::

    zerodb-server
    zerodb-manage
    zerodb-api

These map to the files in the ``zerodbext/server`` directory.

So, to initialize a database, just run::

    $ zerodb-manage init_db

The server runs over TLS. So you have to supply server key and
certificate. If those are not supplied, self-signed certificates will be
generated and stored in `conf/server.pem` and `conf/server_key.pem`.

For authentication, you can use key/certificate pair or username/passphrase.

The simplest is to supply username/passphrase and press <enter> for all other
questions: this will generate server key/certificate pair and create root user.

As a result, the command will create the appropriate database file structure in
``db`` directory and config file
``server.conf`` located in the ``conf`` directory, along with generated
certificate files.
The default administrator
user can create and remove other users or change their public keys.
However, it doesn't have to know any other user's private keys.

Run ``zerodb-server`` and you'll get the ZeroDB server running on the host specified
in the file ``conf/server.conf``.

Healthy output of the running server appears as follows::

    ------
    2016-08-08T02:08:04 INFO ZEO.runzeo (8384) opening storage '1' using FileStorage
    ------
    2016-08-08T02:08:04 INFO ZEO.StorageServer StorageServer created RW with storages: 1:RW:db/db.fs
    ------
    2016-08-08T02:08:04 INFO ZEO.asyncio.mtacceptor listening on ('localhost', 8001)

Adding more users
-----------------

*Warning, this section has to be updated, as well as this section of the code*

Instead of being stored in config files, users are normally stored in a
database. In order to manage these users start the zerodb server and open the
admin console::

    $ zerodb-manage console

This will launch an ipython terminal where you can manage users::

    In [1]: pubkey = get_pubkey("jamesbond", "secure password")
    In [2]: useradd("jamesbond", pubkey)
    In [3]: userdel("jamesbond")

The users you create this way are not administrators and they cannot
manage other users.

.. note:: Press ``Ctrl+D`` to exit the ipython terminal when you're done. (The
   following example code may not work in the admin console.)


Using ZeroDB in Python
======================

Unlike many NoSQL databases, you still define data models in ZeroDB. However,
these are only for indexing, and they are dynamically typed. All the fields you
define in the data models are indexed, but objects which you store in the database
can contain any fields you want (they just won't be indexed).

Let's start by writing a data model in ``demo/models.py`` first:

.. literalinclude:: ../../../zerodb-server/demo/models.py

Let's assume the database server we started before is still running.
The simplest example
which creates records for us would look like this::

    >>> import transaction
    >>> import zerodb
    >>> import models

    >>> db = zerodb.DB(("localhost", 8001), username="root", password="<your passphrase>")
    >>> e = models.Employee(name="John", surname="Smith", salary=150000,
    ...                     description="Coding power")
    >>> db.add(e)
    >>> transaction.commit()

Now, let's do something more advanced and populate the database with random
data using the script ``create.py``:

.. literalinclude:: ../../../zerodb-server/demo/create.py

Let's play with that data in the Python terminal (or you can write your own
script). We'll need to import ``zerodb`` and query operators from
``zerodb.query`` (same syntax as in 
`repoze <http://docs.repoze.org/catalog/usage.html#comparators>`_)::

    >>> import zerodb
    >>> from zerodb.query import *

And we also import our data models::

    >>> from models import *

Let's connect to the database now::

    >>> PASSWORD = "very insecure passphrase - never use it"
    >>> db = zerodb.DB(("localhost", 8001), username="root", password=PASSWORD)

The number of Employees in the database can be determined by just ``len``::

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

To start the API server, make sure you’ve activated the virtual environment and the ZeroDB server is running.
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

