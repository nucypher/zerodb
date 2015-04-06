from zerodb.models import Model
from zerodb import intid


class T(Model):
    pass


def test_initid():
    ts = [T(), T(), T()]

    idstore = intid.IdStore()

    assert len(idstore) == 0

    for t in ts:
        idstore.add(t)

    assert len(idstore) == 3

    for t in ts:
        assert type(t._v_uid) in (int, long)

    assert len(set([t._v_uid for t in ts])) == 3
    assert idstore[ts[0]._v_uid] is ts[0]

    idstore.remove(ts[0])
    idstore.remove(ts[1]._v_uid)

    assert len(idstore) == 1
