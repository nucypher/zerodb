from persistent import Persistent

# constants for indexing operations
UNINDEX = -1
REINDEX = 0
INDEX = 1


class IndexingConfig(Persistent):
    # BBB: support uninstall of 1.x versions
    pass
