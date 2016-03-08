import pickle

import six


class DebugUnpickler(pickle.Unpickler):
    """
    Unpickler which returns class names instead of unpickling (for debug purposes)
    """

    def find_class(self, module, name):
        return name

if six.PY2:
    DebugUnpickler.dispatch[pickle.REDUCE] = lambda x: None


def debug_loads(obj):
    up = DebugUnpickler(six.BytesIO(obj))
    return up.load()
