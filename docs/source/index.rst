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
ZeroDB is end-to-end encrypted (or "zero knowledge") database. It is based on
`ZODB <http://en.wikipedia.org/wiki/Zope_Object_Database>`_ and written in
`Python <https://www.python.org/>`_.

In ZeroDB, client has quite a bit of database logic going on, data encryption,
decryption and compression happens on the client side. Therefore, the server
never has a knowledge about your data or its ordering.

Clients also have an adjustable cache which stores the most used parts of data
structures and greatly speeds up queries even when it's size is small (like 1
megabyte).

From developer's perspective, ZeroDB is designed greatly inspired by `Django
<https://djangoproject.com>`_ ORM and `SQLAlchemy
<http://www.sqlalchemy.org/>`_.


Starting ZeroDB server and creating users
=========================================
We supply Python scripts to run server and manage users who use the database.

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
know anybody's private keys.

Default ``authdb.conf`` contains default ECDSA (`secp256k1
<https://en.bitcoin.it/wiki/Secp256k1>`_) public key for user ``root``. It
corresponds to the passphrase ``"very insecure passphrase - never use it"``:

.. literalinclude:: ../../server/conf/authdb.conf

In order to have correct keys from the very beginning, you can generate a hex
pubkey from any passphrase you like by running ``mkpub.py``.

Running ZeroDB server
---------------------

Just start ``python runserver.py``, and you'll get ZeroDB server running on UNIX
socket ``/tmp/zerosocket``. File ``server.zcml`` allows you to set socket and
other parameters of the server.

Healthy output of the running server looks like the following::

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
database. In order to manage these users start zerodb server and run::

    python manage.py --username root --passphrase "..." --sock /tmp/zerosocket

This will run ipython terminal where you can manage users::

    In [1]: useradd("jamesbond", "secure password")
    In [2]: chpass("jamesbond", "even more secure password")
    In [3]: userdel("jamesbond")

The users you've just created this way are not administrators, and they cannot
manage other users.
Press ``Ctrl+D`` to exit ipython terminal when you're done.


Using ZeroDB in Python
======================

Unlike many NoSQL databases, you still define data models in ZeroDB. However,
these are only for indexing, and they are dynamically typed. All the fields you
define in data models are indexed, and objects which you store in the database
can, in fact, contain any fields not included in the index.

Let's start from writing a data model ``models.py`` first:

.. literalinclude:: ../../experiments/demo/models.py

Now, let's assume we already started the database server. The simplest example
which create records for us would look like this::

    import transaction
    import zerodb
    import models

    db = zerodb.DB("/tmp/zerosocket", username="root", password="...")
    e = models.Employee(name="John", surname="Smith", salary=150000,
                        description="Coding power")
    db.add(e)
    transaction.commit()

Though, let's do something more advanced and populate the database with random
data by a script like this (``create.py``):

.. literalinclude:: ../../experiments/demo/create.py

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

