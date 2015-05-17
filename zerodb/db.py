import transaction
from repoze.catalog.query import optimize
from ZEO import auth
from zerodb.permissions import elliptic

from zerodb.catalog.query import And, Eq
from zerodb.crypto.aes import AES
from zerodb.crypto import sha256
from zerodb import models
from zerodb.models.exceptions import ModelException
from zerodb.permissions import subdb
from zerodb.storage import client_storage
import itertools


class DbModel(object):
    """
    Class where model is combined with db.
    All functionality will actually reside here.
    Will contain indexes as well.
    """
    def __init__(self, db, model):
        """
        :param zerodb.DB db: Database to link model to
        :param model: Data model (subclass of zerodb.models.Model)
        """
        self._model = model
        self._db = db
        self._catalog_name = "catalog__" + model.__modelname__
        self._intid_name = "store__" + model.__modelname__
        if not transaction.manager._txn and \
                (self._intid_name not in db._root or self._catalog_name not in db._root):
            transaction.begin()
            commit = True
        else:
            commit = False
        if self._intid_name in db._root:
            self._objects = db._root[self._intid_name]
        else:
            self._objects = model.create_store()
            db._root[self._intid_name] = self._objects
        if self._catalog_name in db._root:
            self._catalog = db._root[self._catalog_name]
        else:
            self._catalog = model.create_catalog()
            db._root[self._catalog_name] = self._catalog
        if commit:
            transaction.commit()

    def add(self, obj):
        """
        Add newly created a Model object to the database
        Stores *and* indexes it

        :param zerodb.models.Model obj: Object to add to the database
        :return: Added object's uid
        :rtype: int
        """
        assert obj.__class__ == self._model
        uid = self._objects.add(obj)
        self._catalog.index_doc(uid, obj)
        obj._v_uid = uid
        return uid

    def remove(self, obj):
        """
        Remove existing object from the database + unindex it

        :param zerodb.models.Model obj: Object to add to the database
        """
        assert obj.__class__ == self._model
        if isinstance(obj, (int, long)):
            uid = obj
        else:
            uid = obj._v_uid
        self._catalog.unindex_doc(uid)
        del self._objects[uid]

    def query(self, queryobj=None, offset=0, limit=None, **kw):
        """
        Smart proxy to catalog's query.
        One can add <field=...> keyword arguments to make queries where fields
        are equal to specified values

        :param zerodb.catalog.query.Query queryobj: Query which all sorts of
            logical, range queries etc
        :param int offset: Offset to start the result iteration from
        :param int limit: Limit number of results to this
        """
        # Catalog's query returns only integers
        # We must be smart here and return objects
        # But no, we must be even smarter and batch-preload objects
        # Most difficult part is preloading TreeSets for index when needed
        # (when we do complex queries which require composite index)
        # We also probably should do something like lazy query(...)[ofs:...]
        # if no limit, offset are used

        # Work needed on offset and limit because zope didn't well support them...
        if limit:
            kw["limit"] = offset + limit
        # XXX pre-load the tree!

        eq_args = []
        for k in kw.keys():
            if k not in set(["sort_index", "sort_type", "reverse", "names", "limit"]):
                eq_args.append(Eq(k, kw.pop(k)))

        if queryobj:
            Q = optimize(optimize(queryobj) & And(*eq_args))
        else:
            Q = And(*eq_args)

        count, uids = self._catalog.query(Q, **kw)
        if limit:
            qids = itertools.islice(uids, offset, offset + limit)
        else:
            qids = uids
        # No reason to return an iterator as long as we have all pre-loaded
        objects = [self._objects[uid] for uid in qids]
        # Pre-load them all (these are lazy objects)
        if objects:
            self._db._storage.loadBulk([o._p_oid for o in objects])
        for obj, uid in itertools.izip(objects, qids):
            obj._v_uid = uid
        return objects

    def __len__(self):
        return len(self._objects)


class DB(object):
    """
    Database for this user. Everything is used through this class
    """

    db_factory = subdb.DB
    cipher_factory = AES
    auth_module = elliptic

    def __init__(self, sock, username=None, password=None, realm="ZERO", debug=False):
        """
        :param str sock: UNIX (str) or TCP ((str, int)) socket
        :type sock: str or tuple
        :param str username: Username. Derived from password if not set
        :param str password: Password or seed for private key
        :param str realm: ZODB's realm
        :param bool debug: Whether to log debug messages
        """
        if self.auth_module.__module_name__ not in auth._auth_modules:
            self.auth_module.register_auth()
        if not username:
            username = sha256("username" + sha256(password))
        self._storage = client_storage(sock,
                username=username, password=password, realm=realm,
                cipher=DB.cipher_factory(password), debug=debug)
        self._db = DB.db_factory(self._storage)
        self._conn = self._db.open()
        self._root = self._conn.root()
        self._models = {}

    def disconnect(self):
        self._conn.close()

    def __getitem__(self, model):
        """
        DbModels (which we query) are accessed by using db as a dictionary

        :param model: Subclass of zerodb.models.Model to return or create db entry for
        :rtype: zerodb.db.DbModel
        """
        # TODO implement list of keys, writing to arbitrary (new) dbmodel (which is not defined)
        if not issubclass(model, models.Model):
            raise ModelException("Class <%s> is not a Model" % model.__name__)
        if model not in self._models:
            self._models[model] = DbModel(self, model)
        return self._models[model]

    def add(self, obj):
        """
        Add newly created a Model object to the database
        Stores *and* indexes it

        :param zerodb.models.Model obj: Object to add to the database
        :return: Added object's uid
        :rtype: int
        """
        self[obj.__class__].add(obj)

    def remove(self, obj):
        """
        Remove existing object from the database + unindex it

        :param zerodb.models.Model obj: Object to add to the database
        """
        self[obj.__class__].remove(obj)
