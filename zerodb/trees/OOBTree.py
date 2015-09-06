from BTrees.Interfaces import IObjectObjectBTreeModule as IBTreeInterface
import BTrees.OOBTree as TreeModule
from zope.interface import moduleProvides

max_internal_size = 1000
max_leaf_size = 500


class BTree(TreeModule.BTree):
    max_internal_size = max_internal_size
    max_leaf_size = max_leaf_size


class TreeSet(TreeModule.TreeSet):
    max_internal_size = max_internal_size
    max_leaf_size = max_leaf_size


Set = TreeModule.Set
Bucket = TreeModule.Bucket
difference = TreeModule.difference
union = TreeModule.union
intersection = TreeModule.intersection

moduleProvides(IBTreeInterface)
