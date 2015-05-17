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
decryption and compression happens on client side. Therefore, the server
never has any knowledge about the data or its structure/ordering.

Clients also have an adjustable cache which stores the most used parts of data
structures and greatly speeds up queries even when its size is small (e.g. 1
megabyte).

From a developer's perspective, ZeroDB design is greatly inspired by `Django
<https://djangoproject.com>`_'s ORM and `SQLAlchemy
<http://www.sqlalchemy.org/>`_.


Starting the ZeroDB server and creating users
=========================================
We supply Python scripts to run a server and manage users who use the database.

    | conf/
    |   authdb.conf
    |   server.zcml
    | db/
    | manage.py
    | mkpub.py
    | runserver.py

Pre-configure authentication
----------------------------

Config ``authdb.conf`` contains default administrator users for the DB. They can
create and remove other users or change their public keys. However, they don't
know anyone else's private keys.

The default ``authdb.conf`` contains an ECDSA (`secp256k1
<https://en.bitcoin.it/wiki/Secp256k1>`_) public key for user ``root``. It
corresponds to the passphrase ``"very insecure passphrase - never use it"``:

.. literalinclude:: ../../server/conf/authdb.conf

In order to have the correct keys from the very beginning, you can generate a hex
pubkey from any passphrase you like by running ``mkpub.py``.

Running the ZeroDB server
---------------------

Just start ``python runserver.py`` and you'll get the ZeroDB server running on UNIX
socket ``/tmp/zerosocket``. The file ``server.zcml`` allows you to set socket and
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
can, in fact, contain any fields you want (they just won't be included in the index).

Let's start by writing a data model ``models.py`` first:

.. literalinclude:: ../../experiments/demo/models.py

Let's assume we already started the database server. The simplest example
which create records for us would look like this::

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

Let's play with that data in the Python terminal (or you can write your
script)::

    >>> import zerodb
    >>> from zerodb.query import *
    >>> from models import *
    >>> PASSWORD = "very insecure passphrase - never use it"
    >>> db = zerodb.DB("/tmp/zerosocket", username="root", password=PASSWORD)
    >>> len(db[Employee])
    10001
    >>> db[Employee].query(name="John", limit=3)
    [<John Aquirre who earns $147944>, <John Gauthier who earns $169040>, <John
    Hefner who earns $25895>]
    >>> rich_johns = db[Employee].query(InRange("salary", 195000, 200000),
    name="John")
    >>> len(rich_johns)
    5
    >>> from_uk = db[Employee].query(Contains("description", "United Kingdom"))
    >>> from_uk
    [<Stephen Hawking who earns $400000>]
    >>> print from_uk[0].description
    A theoretical physicist, cosmologist,
    author and Director of Research at the Centre for
    Theoretical Cosmology within the University of Cambridge,
    Stephen William Hawking resides in the United Kingom.
    >>> import transaction
    >>> db.remove(from_uk[0])
    >>> transaction.commit()
    >>> len(db[Employee])
    10000

You can do range queries, search the text and remove data from the database.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

