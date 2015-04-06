import ZODB
import transaction
from zerodb import models
from zerodb.models.exceptions import ModelException
from zerodb.storage import client_storage
from zerodb.catalog import Catalog
from zerodb.intid import IdStore


class DbModel(object):
    """
    Class where model is combined with db.
    All functionality will actually reside here.
    Will contain indexes as well.
    """
    def __init__(self, db, model, commit=True):
        self._model = model
        self._db = db
        self._catalog_name = "catalog__" + model.__modelname__
        self._intid_name = "intid__" + model.__modelname__

        if (self._intid_name not in db._root) or (self._catalog_name not in db._root):
            if commit:
                transaction.begin()
            if self._intid_name not in db._root:
                db._root[self._intid_name] = IdStore(family=model.__family__)
            if self._catalog_name not in db._root:
                db._root[self._catalog_name] = Catalog()  # TODO: specify family as a parameter
            if commit:
                transaction.commit()


class DB(object):
    def __init__(self, sock, debug=False):
        """
        :sock - UNIX or TCP socket
        """
        self._storage = client_storage(sock, debug=debug)
        self._db = ZODB.DB(self._storage)
        self._conn = self._db.open()
        self._root = self._conn.root()
        self._models = {}

    def __call__(self, model):
        if not issubclass(model, models.Model):
            raise ModelException("Class <%s> is not a Model" % model.__name__)
        if model not in self._models:
            self._models[model] = DbModel(self, model)
        return self._models[model]
