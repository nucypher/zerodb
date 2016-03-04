# We don't need two-way references given by IntIds, but we need a primary object storage
# If we used IntIds and some objects storage we'd have *3* trees
# But we want to minimize number of calls, so we make one primary IOBTree which has IDs and objects
# Conflict avoidance method is copied from IntIds._generateId (need something better I guess)
import persistent
import random

import six
from BTrees.Length import Length
from zerodb.trees import family32


class IdStore(persistent.Persistent):
    """
    Persistent storage of objects which generates non-conflictiong unique IDs
    for them
    """

    _v_nextid = None

    family = family32

    def __init__(self, family=family32):
        """
        :param family: Family of BTrees to use
        """
        self.tree = family.IO.BTree()
        self.length = Length()

    def _generateId(self):
        """Generate an id which is not yet taken.

        This tries to allocate sequential ids so they fall into the same BTree
        bucket, and randomizes if it stumbles upon a used one.

        This algorithm is taken from zope.intid but it will cause performance
        degradation due to fragmentation if used too often, we need something
        better eventually
        """
        nextid = self._v_nextid
        while True:
            if nextid is None:
                nextid = random.randrange(0, self.family.maxint)
            uid = nextid
            if uid not in self.tree:
                nextid += 1
                if nextid > self.family.maxint:
                    nextid = None
                self._v_nextid = nextid
                return uid
            nextid = None

    def add(self, obj):
        """
        Add object to the storage

        :param obj: Object to store (persistent.Persistent but not necessarily)
        :return: Unique ID
        :rtype: int
        """
        if not hasattr(self, "length"):
            self.length = Length(len(self.tree))
        while True:
            uid = self._generateId()
            if self.tree.insert(uid, obj):  # We use this feature of BTrees to avoid conflicts
                # _v_* and _p_* are not saved in the database
                # However assigning _v_* unghostifies the object while _p_* doesn't
                # We don't want to force-unghostify the object in some cases
                obj._p_uid = uid
                self.length.change(1)
                return uid

    def remove(self, iobj):
        """
        Remove object from the storage
        :param obj: Object or its integer unique id
        """
        if not hasattr(self, "length"):
            self.length = Length(len(self.tree))
        if type(iobj) in six.integer_types:
            del self.tree[iobj]
            self.length.change(-1)
        elif hasattr(iobj, "_p_uid"):
            del self.tree[iobj._p_uid]
            iobj._p_uid = None
            self.length.change(-1)
        else:
            raise TypeError("Argument should be either uid or object itself")

    def __getitem__(self, uid):
        """
        :param int uid: Get object by its unique ID
        """
        return self.tree[uid]

    def __delitem__(self, uid):
        """
        :param int uid: Get object by its unique ID
        """
        self.remove(uid)

    def __len__(self):
        if not hasattr(self, "length"):
            self.length = Length(len(self.tree))
        return self.length.value
