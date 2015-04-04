import pickle
from StringIO import StringIO


class DebugUnpickler(pickle.Unpickler):

    def find_class(self, module, name):
        return name

DebugUnpickler.dispatch[pickle.REDUCE] = lambda x: None


def debug_loads(obj):
    up = DebugUnpickler(StringIO(obj))
    return up.load()
