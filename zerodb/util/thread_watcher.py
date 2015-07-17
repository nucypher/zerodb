# Taken from:
# https://gist.github.com/ajdavis/4644641/

from __future__ import print_function

import threading
import weakref

from functools import partial


class ThreadWatcher(object):
    class Vigil(object):
        pass

    def __init__(self):
        self._refs = {}
        self._local = threading.local()

    def _on_death(self, vigil_id, callback, args, ref):
        self._refs.pop(vigil_id)
        callback(*args)

    def watch(self, callback, *args):
        if not self.is_watching():
            self._local.vigil = v = ThreadWatcher.Vigil()
            on_death = partial(
                self._on_death, id(v), callback, args)

            ref = weakref.ref(v, on_death)
            self._refs[id(v)] = ref

    def is_watching(self):
        "Is the current thread being watched?"
        try:
            v = self._local.vigil
            return id(v) in self._refs
        except AttributeError:
            return False

    def unwatch(self):
        try:
            v = self._local.vigil
            del self._local.vigil
            self._refs.pop(id(v))
        except AttributeError:
            pass
