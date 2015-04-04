from zerodb.catalog import CatalogTextIndex, CatalogFieldIndex


class Indexable(object):
    index_class = None

    def __init__(self, default=None):
        self.default = default

    def __repr__(self):
        return "Indexable field <%s>" % self.__class__.__name__


class Field(Indexable):
    """
    Field of any type which supports comparisions
    """
    index_class = CatalogFieldIndex


class Text(Indexable):
    """
    Text field to be used for fulltext search
    """
    index_class = CatalogTextIndex
