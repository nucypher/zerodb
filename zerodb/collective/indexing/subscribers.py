from zerodb.collective.indexing.queue import getQueue
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.lifecycleevent import ObjectModifiedEvent
from zope.event import subscribers

from zerodb.models import Model


def zerodb_autoreindex_dispatcher(event):
    if isinstance(event, ObjectModifiedEvent) and isinstance(event.object, Model):
        objectAutoReindex(event)


def objectAutoReindex(ev):
    indexer = getQueue()
    indexer.reindex(ev.object, ev.descriptions)   # put into queue, not really reindex.


def init():
    if zerodb_autoreindex_dispatcher not in subscribers:
        subscribers.append(zerodb_autoreindex_dispatcher)
