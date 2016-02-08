from zope.interface import implements
#from Products.Archetypes.CatalogMultiplex import CatalogMultiplex
#from Products.CMFCore.CMFCatalogAware import CMFCatalogAware
from zerodb.collective.indexing.interfaces import IIndexQueueProcessor


# container to hold references to the original and "monkeyed" indexing methods
# these are populated by `collective.indexing.monkey`
catalogMultiplexMethods = {}
catalogAwareMethods = {}
monkeyMethods = {}


def getOwnIndexMethod(obj, name):
    """ return private indexing method if the given object has one """
    attr = getattr(obj.__class__, name, None)
    if attr is not None:
        method = attr.im_func
        monkey = monkeyMethods.get(name.rstrip('Object'), None)
        if monkey is not None and method is not monkey:
            return method


class IPortalCatalogQueueProcessor(IIndexQueueProcessor):
    """ an index queue processor for the standard portal catalog via
        the `CatalogMultiplex` and `CMFCatalogAware` mixin classes """


class PortalCatalogProcessor(object):
    implements(IPortalCatalogQueueProcessor)

    def index(self, obj, attributes=None):
        #index(obj, attributes)
        pass

    def reindex(self, obj, attributes=None):
        #reindex(obj, attributes)
        pass

    def unindex(self, obj):
        #unindex(obj)
        pass

    def begin(self):
        pass

    def commit(self):
        pass

    def abort(self):
        pass
