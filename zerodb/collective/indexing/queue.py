from logging import getLogger
from threading import local
from zope.interface import implements
from zope.component import getSiteManager
from Acquisition import aq_base, aq_inner, aq_parent

from zerodb.collective.indexing.interfaces import IIndexQueue
from zerodb.collective.indexing.interfaces import IIndexQueueProcessor
from zerodb.collective.indexing.config import INDEX, REINDEX, UNINDEX
from zerodb.collective.indexing.transactions import QueueTM

debug = getLogger('collective.indexing.queue').debug


localQueue = None
processing = set()


class InvalidQueueOperation(Exception):
    pass


def getQueue():
    """ return a (thread-local) queue object, create one if necessary """
    global localQueue
    if localQueue is None:
        localQueue = IndexQueue()
    return localQueue


def processQueue():
    """ process the queue (for this thread) immediately """
    queue = getQueue()
    processed = 0
    if queue.length() and not queue in processing:
        debug('auto-flushing %d items: %r', queue.length(), queue.getState())
        try:
            processing.add(queue)
            processed = queue.process()
        finally:
            processing.remove(queue)
    return processed


def wrap(obj):
    """ the indexing key, i.e. the path to the object in the case of the
        portal catalog, might have changed while the unindex operation was
        delayed, for example due to renaming the object;  it was probably not
        such a good idea to use a key that can change in the first place, but
        to work around this a proxy object is used, which can provide the
        original path;  of course, access to other attributes must still be
        possible, since alternate indexers (i.e. solr etc) might use another
        unique key, usually the object's uid;  also the inheritence tree
        must match """
    if getattr(aq_base(obj), 'getPhysicalPath', None) is None:
        return obj

    class PathWrapper(obj.__class__):

        def __init__(self):
            self.__dict__.update(dict(
                context = obj,
                path = obj.getPhysicalPath(),
                REQUEST = getattr(obj, 'REQUEST', None)))

        def __getattr__(self, name):
            return getattr(aq_inner(self.context), name)

        def __hash__(self):
            return hash(self.context)   # make the wrapper transparent...

        def getPhysicalPath(self):
            return self.path

    return PathWrapper().__of__(aq_parent(obj))


class IndexQueue(local):

    implements(IIndexQueue)

    def __init__(self):
        self.queue = []
        self.tmhook = None

    def hook(self):
        """ register a hook into the transaction machinery if that hasn't
            already been done;  this is to make sure the queue's processing
            method gets called back just before the transaction is about to
            be committed """
        if self.tmhook is None:
            self.tmhook = QueueTM(self).register
        self.tmhook()

    def index(self, obj, attributes=None):
        self.queue.append((INDEX, obj, attributes))
        self.hook()

    def reindex(self, obj, attributes=None):
        self.queue.append((REINDEX, obj, attributes))
        self.hook()

    def unindex(self, obj):
        self.queue.append((UNINDEX, wrap(obj), None))
        self.hook()

    def setHook(self, hook):
        self.tmhook = hook

    def getState(self):
        return list(self.queue)     # better return a copy... :)

    def setState(self, state):
        self.queue = state

    def length(self):
        """ return number of currently queued items;  please note that
            we cannot use `__len__` here as this will cause test failures
            due to the way objects are compared """
        return len(self.queue)

    def optimize(self):
        res = {}
        for iop, obj, iattr in self.getState():
            oid = hash(obj)
            func = getattr(obj, 'getPhysicalPath', None)
            if callable(func):
                oid = oid, func()
            op, dummy, attr = res.get(oid, (0, obj, iattr))
            # If we are going to delete an item that was added in this transaction, ignore it
            if op == INDEX and iop == UNINDEX:
                del res[oid]
            else:
                # Operators are -1, 0 or 1 which makes it safe to add them
                op += iop
                op = min(max(op, UNINDEX), INDEX) # operator always between -1 and 1

                # Handle attributes, None means all fields, and takes presedence
                if isinstance(attr, (tuple, list)) and isinstance(iattr, (tuple, list)):
                    attr = tuple(set(attr).union(iattr))
                else:
                    attr = None

                res[oid] = (op, obj, attr)

        debug('finished reducing; %d item(s) in queue...', len(res))
        # Sort so unindex operations come first
        self.setState(sorted(res.values()))

    def process(self):
        print("###process queue")
        self.optimize()
        if not self.queue:
            return 0
        sm = getSiteManager()
        print("###sm:",sm)
        utilities = list(sm.getUtilitiesFor(IIndexQueueProcessor))
        print("##len of util:", len(utilities))
        processed = 0
        for name, util in utilities:
            util.begin()
        # TODO: must the queue be handled independently for each processor?
        for op, obj, attributes in self.queue:
            print("###obj:",obj)
            for name, util in utilities:
                print("##util:",util)
                if op == INDEX:
                    util.index(obj, attributes)
                elif op == REINDEX:
                    print("##really reindex")
                    util.reindex(obj, attributes)
                elif op == UNINDEX:
                    util.unindex(obj)
                else:
                    raise InvalidQueueOperation(op)
            processed += 1
        debug('finished processing %d items...', processed)
        self.clear()
        return processed

    def commit(self):
        sm = getSiteManager()
        for name, util in sm.getUtilitiesFor(IIndexQueueProcessor):
            util.commit()

    def abort(self):
        sm = getSiteManager()
        for name, util in sm.getUtilitiesFor(IIndexQueueProcessor):
            util.abort()
        self.clear()

    def clear(self):
        del self.queue[:]
        # release transaction manager
        self.tmhook = None
