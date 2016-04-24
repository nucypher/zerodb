import itertools
import os
import threading

import six
from six.moves import zip as izip
from Crypto import Random
import transaction

from hashlib import sha256
from zerodbext.catalog.query import optimize
from zerodb.collective.indexing.indexer import PortalCatalogProcessor
from zerodb.collective.indexing.interfaces import IIndexQueueProcessor
from zerodb.collective.indexing import subscribers
from zope import component
from zerodb.permissions import elliptic

from zerodb import models
from zerodb.catalog.query import And, Eq
from zerodb.models.exceptions import ModelException
from zerodb.permissions import subdb
from zerodb.storage import client_storage
from zerodb.util.thread_watcher import ThreadWatcher
from zerodb.util.iter import DBList, DBListPrefetch, Sliceable

from zerodb.transform.encrypt_aes import AES256Encrypter, AES256EncrypterV0
from zerodb.transform import init_crypto


class AutoReindexQueueProcessor(PortalCatalogProcessor):
    def __init__(self, db, enabled=True):
        self.db = db
        self.enabled = enabled

    def reindex(self, obj, attributes=None):   # execute reindex in before_commit hook when commit
        if self.enabled:
            self.db.reindex(obj, attributes)


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

        if self._intid_name not in db._root:
            _objects = model.create_store()
            db._root[self._intid_name] = _objects

        if self._catalog_name not in db._root:
            _catalog = model.create_catalog()
            db._root[self._catalog_name] = _catalog

        if commit:
            transaction.commit()

    @property
    def _catalog(self):
        return self._db._root[self._catalog_name]

    @property
    def _objects(self):
        return self._db._root[self._intid_name]

    def __getitem__(self, uids):
        """
        DbModels (which we query) are accessed by using db as a dictionary

        :param int uids: object's uid or list of them
        :return: Persistent object(s)
        """
        if isinstance(uids, six.integer_types):
            obj = self._objects[uids]
            if not hasattr(obj, "_p_uid"):
                obj._p_uid = uids
            return obj

        elif isinstance(uids, (tuple, list, set)):
            objects = [self._objects[uid] for uid in uids]
            self._db._storage.loadBulk([o._p_oid for o in objects])
            for o, uid in izip(objects, uids):
                if not hasattr(o, "_p_uid"):
                    o._p_uid = uid
            return objects

        else:
            raise ModelException("Integer or list of integers is expected")

    def all_uids(self):
        for i in self._objects.tree:
            yield i

    def all(self):
        for i in self.all_uids():
            obj = self._objects[i]
            if not hasattr(obj, "_p_uid"):
                obj._p_uid = i
            yield obj

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
        obj._p_uid = uid
        return uid

    def reindex_one(self, obj, attributes=None):
        """
        Reindex one object which is already in the database

        :param obj: Object to add to the database or its uid
        :type obj: zerodb.models.Model, int
        :param attributes: Attributes of obj to be reindex
        :type attributes: tuple, list
        """

        if isinstance(obj, six.integer_types):
            uid = obj
            obj = self._objects[uid]
        elif isinstance(obj, self._model):
            if hasattr(obj, "_p_uid"):
                uid = obj._p_uid
            else:
                raise ModelException("Object %s is not indexed" % obj)
        else:
            raise TypeError("Wrong type of argument passed: obj must be integer or model instance")

        if attributes is None:
            self._catalog.reindex_doc(uid, obj)
        elif isinstance(attributes, (tuple, list)):
            for attr in attributes:
                if attr in self._catalog:
                    self._catalog[attr].reindex_doc(uid, obj)
        else:
            raise TypeError("Wrong type of argument passed: attributes must be tuple or list")

    def reindex(self, obj):
        """
        Reindex one or multiple objects in the database

        :param obj: Object to add to the database or its uid, or list of objects or uids
        :type obj: zerodb.models.Model, int, list
        """
        if isinstance(obj, six.integer_types) or isinstance(obj, self._model):
            self.reindex_one(obj)
        elif isinstance(obj, (list, tuple, set, Sliceable)):
            for o in obj:
                self.reindex_one(o)
        else:
            raise TypeError("ZeroDB object, its uid or list of these should be passed")

    def remove(self, obj):
        """
        Remove existing object from the database + unindex it

        :param zerodb.models.Model obj: Object to add to the database
        """
        if isinstance(obj, six.integer_types):
            uid = obj
        elif hasattr(obj, "__iter__"):
            ctr = 0
            for i in list(obj):
                self.remove(i)
                ctr += 1
            return ctr
        else:
            assert obj.__class__ == self._model
            uid = obj._p_uid
        self._catalog.unindex_doc(uid)
        del self._objects[uid]
        return 1

    def query(self, queryobj=None, skip=None, limit=None, prefetch=True, **kw):
        """
        Smart proxy to catalog's query.
        One can add <field=...> keyword arguments to make queries where fields
        are equal to specified values

        :param zerodb.catalog.query.Query queryobj: Query which all sorts of
            logical, range queries etc
        :param int skip: Offset to start the result iteration from
        :param int limit: Limit number of results to this
        """
        # Catalog's query returns only integers
        # We must be smart here and return objects
        # But no, we must be even smarter and batch-preload objects
        # Most difficult part is preloading TreeSets for index when needed
        # (when we do complex queries which require composite index)
        # We also probably should do something like lazy query(...)[ofs:...]
        # if no limit, skip are used

        # Work needed on skip and limit because zope didn't well support them...
        skip = skip or 0
        if limit:
            kw["limit"] = skip + limit

        eq_args = []
        for k in list(kw.keys()):
            if k not in set(["sort_index", "sort_type", "reverse", "names", "limit"]):
                eq_args.append(Eq(k, kw.pop(k)))

        if queryobj:
            Q = optimize(optimize(queryobj) & And(*eq_args))
        else:
            Q = And(*eq_args)

        q = lambda: self._catalog.query(Q, **kw)

        if limit:
            _, q = q()
            # XXX islice -> [:]
            qids = list(itertools.islice(q, skip, skip + limit))
            objects = [self._objects[uid] for uid in qids]
            if objects and prefetch:
                self._db._storage.loadBulk([o._p_oid for o in objects])
            for obj, uid in izip(objects, qids):
                obj._p_uid = uid
            return objects

        else:
            db_list = DBListPrefetch if prefetch else DBList
            return db_list(q, self)

    def __len__(self):
        return len(self._objects)


class DB(object):
    """
    Database for this user. Everything is used through this class
    """

    db_factory = subdb.DB
    auth_module = elliptic
    encrypter = [AES256Encrypter, AES256EncrypterV0]
    compressor = None

    def __init__(self, sock, username=None, password=None, realm="ZERO", debug=False, pool_timeout=3600, pool_size=7, autoreindex=True, **kw):
        """
        :param str sock: UNIX (str) or TCP ((str, int)) socket
        :type sock: str or tuple
        :param str username: Username. Derived from password if not set
        :param str password: Password or seed for private key
        :param str realm: ZODB's realm
        :param bool debug: Whether to log debug messages
        """

        # ZODB doesn't like unicode here
        username = username and str(username)
        password = str(password)

        if isinstance(sock, six.string_types):
            sock = str(sock)
        elif type(sock) in (list, tuple):
            assert len(sock) == 2
            sock = str(sock[0]), int(sock[1])

        self._autoreindex = autoreindex
        self._reindex_queue_processor = AutoReindexQueueProcessor(self, enabled=autoreindex)
        component.provideUtility(self._reindex_queue_processor, IIndexQueueProcessor, 'zerodb-indexer')

        self.auth_module = kw.pop("auth_module", self.auth_module)

        self.auth_module.register_auth()
        if not username:
            username = sha256("username" + sha256(password).digest()).digest()

        self._init_default_crypto(passphrase=password)

        # Store all the arguments necessary for login in this instance
        self.__storage_kwargs = {
                "sock": sock,
                "username": username,
                "password": password,
                "realm": realm,
                "cache_size": 2 ** 30,
                "debug": debug}

        self.__db_kwargs = {
                "pool_size": pool_size,
                "pool_timeout": pool_timeout,
                "cache_size": 1000000,
                "cache_size_bytes": 100 * 2 ** 20}
        self.__db_kwargs.update(kw)

        # For multi-threading
        self.__pid = os.getpid()

        self._init_db()
        self._models = {}

    @classmethod
    def _init_default_crypto(self, passphrase=None):
        encrypters = self.encrypter
        if not isinstance(encrypters, (list, tuple)):
            encrypters = [self.encrypter]
        elif not encrypters:
            encrypters = []

        if encrypters:
            encrypters[0].register_class(default=True)
            for e in encrypters[1:]:
                e.register_class(default=False)
        if self.compressor:
            self.compressor.register(default=True)

        init_crypto(passphrase=passphrase)

    def _init_db(self):
        """We need this to be executed each time we are in a new process"""
        if self._autoreindex:
            subscribers.init()

        Random.atfork()

        self.__conn_refs = {}
        self.__thread_local = threading.local()
        self.__thread_watcher = ThreadWatcher()
        self._storage = client_storage(**self.__storage_kwargs)
        self._db = DB.db_factory(self._storage, **self.__db_kwargs)
        self._conn_open()

    def _conn_open(self):
        """Opens db connection and registers a destuction callback"""

        self.__thread_local.conn = conn = self._db.open()

        def destructor(conn_id):
            conn = self._db.pool.all.data.get(conn_id, None)
            if conn:
                # Hack to make it not closing TM which is already removed
                conn.opened = 0
                conn.close()

        self.__thread_watcher.watch(destructor, id(conn))

    @property
    def _root(self):
        """Access database root for this user"""

        if os.getpid() != self.__pid:
            # If a new process spins up, we need to re-initialize everything
            self.__pid = os.getpid()
            self._init_db()
        else:
            # Open connections from the pool when new threads spin up
            # Should be closed when old thread-locals get garbage collected
            if not hasattr(self.__thread_local, "conn") or\
                    self.__thread_local.conn.opened is None:
                self._conn_open()

        return self.__thread_local.conn.root()

    @property
    def _connection(self):
        return self.__thread_local.conn

    def disconnect(self):
        if hasattr(self.__thread_local, "conn"):
            self.__thread_local.conn.close()

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
        if isinstance(obj, (list, set, tuple)):
            return [self[o.__class__].add(o) for o in obj]
        else:
            return self[obj.__class__].add(obj)

    def remove(self, obj):
        """
        Remove existing object from the database + unindex it

        :param zerodb.models.Model obj: Object to add to the database
        """
        if isinstance(obj, models.Model):
            self[obj.__class__].remove(obj)
            return 1
        elif hasattr(obj, "__iter__"):
            ctr = 0
            for o in obj:
                ctr += 1
                self[o.__class__].remove(o)
            return ctr
        else:
            raise ModelException("Class <%s> is not a Model or iterable" % obj.__class__.__name__)

    def reindex(self, obj, attributes=None):
        """
        Reindex one or multiple objects in the database

        :param obj: Object to add to the database or its uid, or list of objects or uids
        :type obj: zerodb.models.Model, list
        :param attributes: Attributes of obj to be reindex
        :type attributes: tuple, list
        """
        if isinstance(obj, models.Model):
            self[obj.__class__].reindex_one(obj, attributes)
        elif isinstance(obj, (list, tuple, set, Sliceable)):
            for o in obj:
                assert isinstance(o, models.Model)
                self[o.__class__].reindex_one(o, attributes)
        else:
            raise TypeError("ZeroDB object or list of these should be passed")

    def pack(self):
        """
        Remove old versions of objects
        """
        self._db.pack()

    def enableAutoReindex(self, enabled=True):
        """
        Enable or disable auto reindex
        """
        if enabled:
            subscribers.init()
        self._reindex_queue_processor.enabled = enabled
