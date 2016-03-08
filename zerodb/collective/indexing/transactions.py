from logging import getLogger
from threading import local
from transaction.interfaces import ISavepointDataManager
from transaction import get as getTransaction
from zope.interface import implementer

logger = getLogger('collective.indexing.transactions')


class QueueSavepoint(object):
    """ transaction savepoints using the IIndexQueue interface """

    def __init__(self, queue):
        self.queue = queue
        self.state = queue.getState()

    def rollback(self):
        self.queue.setState(self.state)


@implementer(ISavepointDataManager)
class QueueTM(local):
    """ transaction manager hook for the indexing queue """

    def __init__(self, queue):
        local.__init__(self)
        self.registered = False
        self.vote = False
        self.queue = queue

    def register(self):
        if not self.registered:
            try:
                transaction = getTransaction()
                transaction.join(self)
                transaction.addBeforeCommitHook(self.before_commit)
                self.registered = True
            except Exception:
                logger.exception('Exception during register (registered=%s)',
                    self.registered)

    def savepoint(self):
        return QueueSavepoint(self.queue)

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        pass

    def before_commit(self):
        self.queue.process()
        self.queue.clear()

    def tpc_vote(self, transaction):
        pass

    def tpc_finish(self, transaction):
        self.queue.commit()
        self.registered = False

    def tpc_abort(self, transaction):
        self.queue.abort()
        self.queue.clear()
        self.registered = False

    abort = tpc_abort

    def sortKey(self):
        return str(id(self))
