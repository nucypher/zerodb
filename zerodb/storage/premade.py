"""
Most common classes of storages
"""

from .multi import MultiStorage
from .batch import ZEOBatchStorage


class DefaultServerStorage(ZEOBatchStorage, MultiStorage):
    pass
