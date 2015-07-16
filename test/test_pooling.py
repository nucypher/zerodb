import ctypes
import multiprocessing
import threading

from db import Page

id_conn_child = None


def test_thread_pooling(db):
    id_conn_parent = id(db._connection)

    def f():
        global id_conn_child

        db._root  # connect automatically
        id_conn_child = id(db._connection)

    thread = threading.Thread(target=f)
    thread.start()
    thread.join()

    # Threadlocals die only when another thread accesses them
    db._root

    # TODO: close connection when thread dies
    # assert len(db._db.pool.all) == 1

    # Test that child used connection other than parent
    assert id_conn_child != id_conn_parent
    assert id_conn_child is not None


def test_forking(db):
    id_conn_parent = id(db._connection)
    id_conn_child = multiprocessing.Value(ctypes.c_int64)

    def f():
        assert len(db[Page]) > 0  # Check that DB is functional in the subprocess
        id_conn_child.value = id(db._connection)

    p = multiprocessing.Process(target=f)
    p.start()
    p.join()

    # Teest that child used connection other than parent
    assert id_conn_child.value != 0
    assert id_conn_child.value != id_conn_parent
