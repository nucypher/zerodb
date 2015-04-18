from zerodb.catalog.indexes.text import CatalogTextIndex
from zerodb.catalog.indexes.field import CatalogFieldIndex
import exceptions


class Indexable(object):
    Index = None

    def __init__(self, default=None, virtual=None):
        """
        default -- default value (which can be callable, like utcnow)
        virtual -- virtual value which is *only* calculated but is not stored
        """
        self.default = default
        self.virtual = virtual

        if (self.default is not None) and (self.virtual is not None):
            raise exceptions.FieldException("One cannot simultaneously set the default value and claim that the field is derived by calculation only")

    def __repr__(self):
        return "Indexable field <%s>" % self.__class__.__name__


class Field(Indexable):
    """
    Field of any type which supports comparisions
    """
    Index = CatalogFieldIndex


class Text(Indexable):
    """
    Text field to be used for fulltext search
    """
    Index = CatalogTextIndex
