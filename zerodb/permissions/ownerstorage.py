from ZODB.POSException import POSKeyError, StorageError
from ZODB.utils import maxtid, u64, z64
import ZODB.interfaces
import zope.interface

@zope.interface.implementer(ZODB.interfaces.IMultiCommitStorage)
class OwnerStorage(object):
    """Storage wrapper that adds/stript/checks owner id in record

    Some special considerations around bootstrapping:

    - Except for the root users, users' ids are their root folder's
      oids.  This allows us to grant access even when a user's root
      folder was written by the root user.  Note that once a user
      modified their root folder, the root user won't have access.

    - All user can access object 0, but they can't access any
      persistent subobjects of it.
    """

    # methods we punt on:
    history = load = restore = iterator = undo = undoLog = undoInfo = None
    record_iternext = storeBlob = loadBlob = restoreBlob = None
    def __iter__(self):
        if False: yield
    def supportsUndo(self):
        return False

    def __init__(self, storage, user_id):
        self.user_id = user_id
        self.storage = storage

    def __getattr__(self, name):
        return getattr(self.storage, name)

    def _check_permissions(self, data, oid=None):
        if not (
            data.endswith(self.user_id) or
            oid == self.user_id or
            oid == z64
            ):
            raise StorageError(
                "Attempt to access encrypted data of others at <%s> by <%s>" % (
                    u64(oid), u64(self.user_id)))

    def loadBefore(self, oid, tid):
        r = self.storage.loadBefore(oid, tid)
        if r is not None:
            data, serial, after = r
            self._check_permissions(data, oid)
            return data[:-len(self.user_id)], serial, after
        else:
            return r

    def loadSerial(self, oid, serial):
        r = self.storage.loadSerial(oid, tid)
        data = self.storage.loadSerial(self, oid, serial)
        self._check_permissions(data, oid)
        return data[:-len(self.user_id)]

    def store(self, oid, serial, data, version, transaction):
        try:
            old_data = self.storage.loadBefore(oid, maxtid)[0]
            self._check_permissions(old_data, oid)
        except POSKeyError:
            pass  # We store a new one
        data += self.user_id
        self.storage.store(oid, serial, data, version, transaction)

    def __len__(self):
        return len(self.storage)
