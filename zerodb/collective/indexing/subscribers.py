from Acquisition import aq_parent, aq_inner, aq_base
from zope.container.contained import dispatchToSublocations
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent, Attributes
from zope.publisher.interfaces.browser import IBrowserRequest

from zerodb.collective.indexing.queue import getQueue


def filterTemporaryItems(obj, checkId=True):
    """ check if the item has an acquisition chain set up and is not of
        temporary nature, i.e. still handled by the `portal_factory`;  if
        so return it, else return None """
    parent = aq_parent(aq_inner(obj))
    if parent is None:
        return None
    if IBrowserRequest.providedBy(parent):
        return None
    if checkId and getattr(obj, 'getId', None):
        parent = aq_base(parent)
        if getattr(parent, '__contains__', None) is None:
            return None
        elif obj.getId() not in parent:
            return None
    isTemporary = getattr(obj, 'isTemporary', None)
    if isTemporary is not None:
        try:
            if obj.isTemporary():
                return None
        except TypeError:
            return None # `isTemporary` on the `FactoryTool` expects 2 args
    return obj


def objectAdded(ev):
    obj = filterTemporaryItems(ev.object)
    indexer = getQueue()
    if obj is not None and indexer is not None:
        indexer.index(obj)


def objectModified(ev):
    obj = filterTemporaryItems(ev.object)
    indexer = getQueue()
    if obj is None or indexer is None:
        return
    if getattr(ev, 'descriptions', None):   # not used by archetypes/plone atm
        # build the list of to be updated attributes
        attrs = []
        for desc in ev.descriptions:
            if isinstance(desc, Attributes):
                attrs.extend(desc.attributes)
        indexer.reindex(obj, attrs)
        if 'allow' in attrs:    # dispatch to sublocations on security changes
            dispatchToSublocations(ev.object, ev)
    else:
        # with no descriptions (of changed attributes) just reindex all
        indexer.reindex(obj)


def objectCopied(ev):
    objectAdded(ev)


def objectRemoved(ev):
    obj = filterTemporaryItems(ev.object, checkId=False)
    indexer = getQueue()
    if obj is not None and indexer is not None:
        indexer.unindex(obj)


def objectMoved(ev):
    if ev.newParent is None or ev.oldParent is None:
        # it's an IObjectRemovedEvent or IObjectAddedEvent
        return
    if ev.newParent is ev.oldParent:
        # it's a renaming operation
        dispatchToSublocations(ev.object, ev)
    obj = filterTemporaryItems(ev.object)
    indexer = getQueue()
    if obj is not None and indexer is not None:
        indexer.index(obj)


def dispatchObjectMovedEvent(ob, ev):
    """ dispatch events to sub-items when a folderish item has been renamed """
    if ob is not ev.object:
        if ev.oldParent is ev.newParent:
            notify(ObjectModifiedEvent(ob))


def objectTransitioned(ev):
    obj = filterTemporaryItems(ev.object)
    indexer = getQueue()
    if obj is not None and indexer is not None:
        indexer.reindex(obj)
