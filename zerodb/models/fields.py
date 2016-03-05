from zerodb.catalog.indexes.text import CatalogTextIndex, CatalogTextIndexOkapi
from zerodb.catalog.indexes.field import CatalogFieldIndex
from . import exceptions


class Indexable(object):
    Index = None

    def __init__(self, default=None, virtual=None, index=True):
        """
        :param default: Default value (which can be callable, like utcnow)
        :param virtual: Virtual value which is *only* calculated but is not
            stored. Still, it is indexed
        :param bool index: If False, we just use schema for validation
        """
        self.default = default
        self.virtual = virtual
        self.indexed = index

        if (default is not None) and (virtual is not None):
            raise exceptions.FieldException("One cannot simultaneously set the default value"
                                            "and claim that the field is derived by calculation only")

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


class TextOkapi(Indexable):
    Index = CatalogTextIndexOkapi
