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
ZeroDB is an end-to-end encrypted (or "zero knowledge") database. It is based on
`ZODB <http://en.wikipedia.org/wiki/Zope_Object_Database>`_ and written in
`Python <https://www.python.org/>`_.

In ZeroDB, the client is responsible for the database logic. Data encryption,
decryption and compression also happen client side. Therefore, the server
never has any knowledge about the data, its structure or order.

Clients also have an adjustable cache which stores the most used parts of data
structures and greatly speeds up queries even when its size is small (e.g. 1
megabyte).

From a developer's perspective, ZeroDB's design is greatly inspired by the `Django
<https://djangoproject.com>`_ ORM and `SQLAlchemy
<http://www.sqlalchemy.org/>`_.

Installation
============
We supply ZeroDB as a Python egg package ``zerodb-0.8-py2.7.egg``. You could
install it using ``easy_install``.

However, let's install everything in a virtual environment to run the server and
test scripts. Clone the ``zerodb-server`` repository, navigate to the
resulting directory and run::

    ./virtualenv.sh

This installs everything you need into the directory ``.venv``, which you can
activate using::

    source activate

The scripts in the ``server`` and ``demo`` directories will now run in this
virtual environment.

Starting the ZeroDB server and creating users
=========================================
In the ``server`` directory, we supply Python scripts to run a server and
manage users.

    | conf/
    |   authdb.conf
    |   server.zcml
    | db/
    | manage.py
    | mkpub.py
    | runserver.py

Pre-configure authentication
----------------------------

The config file ``authdb.conf`` contains default administrator users for
the database. These admins can create and remove other users or change their
public keys. However, they don't know any other user's private keys.

The default ``authdb.conf`` contains an ECDSA (`secp256k1
<https://en.bitcoin.it/wiki/Secp256k1>`_) public key for the user ``root``. It
corresponds to the passphrase ``"very insecure passphrase - never use it"``:

.. literalinclude:: ../../server/conf/authdb.conf

In order to create secure keys, you can generate a hex pubkey from any passphrase
you like by running ``python mkpub.py``. Be sure to put the resulting pubkey into
``authdb.conf`` yourself, before the running ZeroDB for the first time.

Running the ZeroDB server
---------------------

Just start ``python runserver.py`` and you'll get the ZeroDB server running on a UNIX
socket ``/tmp/zerosocket``. The file ``server.zcml`` allows you to set the socket and
other parameters of the server.

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
    2015-05-16T16:01:53 INFO ZEO.zrpc (6580) listening on /tmp/zerosocket

Adding more users
-----------------

Instead of being stored in config files, users are normally stored in a
database. In order to manage these users start the zerodb server and run::

    python manage.py --username root --passphrase "..." --sock /tmp/zerosocket

This will run an ipython terminal where you can manage users::

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

.. literalinclude:: ../../experiments/demo/models.py

Let's assume the database server we started before is still running. The simplest example
which creates records for us would look like this::

    import transaction
    import zerodb
    import models

    db = zerodb.DB("/tmp/zerosocket", username="root", password="...")
    e = models.Employee(name="John", surname="Smith", salary=150000,
                        description="Coding power")
    db.add(e)
    transaction.commit()

Now, let's do something more advanced and populate the database with random
data using the script ``create.py``:

.. literalinclude:: ../../experiments/demo/create.py

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
    >>> db = zerodb.DB("/tmp/zerosocket", username="root", password=PASSWORD)

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

Let's remove the record from the last example. We'll need the ``tranaction``
module for that::

    >>> import transaction
    >>> db.remove(from_uk[0])
    >>> transaction.commit()
    >>> len(db[Employee])
    10000

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

