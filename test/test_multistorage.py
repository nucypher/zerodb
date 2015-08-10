from zerodb.storage import multi


def test_multistorage():
    class X(object):
        def _x(self):
            pass

        def x(self):
            pass

        def loadEx(self, x):
            return x

    class Y(object):
        def y(self):
            pass

        def z(self):
            pass

        extensions = [y]

    class M(X, Y, multi.MultiStorage):
        pass

    assert len(M.extensions) == 2
    m = M(None)
    m.x()
    m.y()
    assert m.loadEx(42) == 42
