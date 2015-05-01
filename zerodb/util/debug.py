import pickle
from StringIO import StringIO


class DebugUnpickler(pickle.Unpickler):
    """
    Unpickler which returns class names instead of unpickling (for debug purposes)
    """

    def find_class(self, module, name):
        return name

DebugUnpickler.dispatch[pickle.REDUCE] = lambda x: None


def debug_loads(obj):
    up = DebugUnpickler(StringIO(obj))
    return up.load()
