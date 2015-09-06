from BTrees.Interfaces import IIntegerIntegerBTreeModule as IBTreeInterface
import BTrees.IIBTree as TreeModule
from zope.interface import moduleProvides

max_internal_size = 2850
max_leaf_size = 1425


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
multiunion = TreeModule.multiunion
weightedUnion = TreeModule.weightedUnion
weightedIntersection = TreeModule.weightedIntersection

moduleProvides(IBTreeInterface)
