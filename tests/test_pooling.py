import ctypes
import multiprocessing
import threading
import gc

from time import sleep

from db import Page

id_conn_child = None


def test_thread_pooling(db):
    id_conn_parent = id(db._connection)

    def f():
        global id_conn_child

        assert len(db[Page]) > 0  # connect automatically
        id_conn_child = id(db._connection)
        sleep(0.2)

    thread = threading.Thread(target=f)
    thread.start()
    sleep(0.1)
    assert len(db._db.pool.all) - len(db._db.pool.available) == 2

    thread.join()

    # Threadlocals die only when another thread accesses them
    db._root
    sleep(0.3)

    gc.collect()

    # TODO: close connection when thread dies
    assert len(db._db.pool.all) - len(db._db.pool.available) == 1

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
    p.daemon = True
    p.start()
    p.join(10)

    # Test that child used connection other than parent
    assert id_conn_child.value != 0
    assert id_conn_child.value != id_conn_parent
