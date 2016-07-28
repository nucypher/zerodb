"""Convenience to start ZeroDB servers from Python

Forked :) from ZEO.tests.forker
"""
import logging
import os
import tempfile
import threading
from six.moves.queue import Empty

from ZEO.tests.forker import stop_runner, whine
from ZODB.utils import z64
import ZEO.tests.testssl
import ZODB

from .permissions import subdb, base

logger = logging.getLogger(__name__)

def runner(config, qin, qout, timeout=None,
           debug=False, name=None,
           keep=False, init=True):

    if debug:
        from ZEO.tests.forker import debug_logging
        debug_logging()

    try:

        options = subdb.ZeroDBOptions()
        options.realize(['-C', config])
        server = subdb.ZEOServer(options)
        globals()[(name if name else 'last') + '_server'] = server
        server.open_storages()

        if init:
            password=None
            if isinstance(init, str):
                client_cert = init
            elif isinstance(init, dict):
                client_cert = init.get('cert')
                password = init.get('password')
            else:
                assert init is True
                client_cert = ZEO.tests.testssl.client_cert

            if client_cert:
                with open(client_cert) as f:
                    pem_data = f.read()
            else:
                pem_data = None

            [storage] = server.storages.values()
            base.init_db(storage, 'root', pem_data, False, password=password)

        server.clear_socket()
        server.create_server()
        logger.debug('SERVER CREATED')
        qout.put(server.server.acceptor.addr)
        logger.debug('ADDRESS SENT')
        thread = threading.Thread(
            target=server.server.loop, kwargs=dict(timeout=.2),
            name = None if name is None else name + '-server',
            )
        thread.setDaemon(True)
        thread.start()

        try:
            qin.get(timeout=timeout)
        except Empty:
            pass
        server.server.close()
        thread.join(3)

        if not keep:
            # Try to cleanup storage files
            for storage in server.server.storages.values():
                try:
                    storage.cleanup()
                except AttributeError:
                    pass

        qout.put(thread.is_alive())
        qin.get(timeout=11) # ack
        if hasattr(qout, 'close'):
            qout.close()
            qout.cancel_join_thread()

    except Exception:
        logger.exception("In server thread")

def start_server(storage_conf=None, zeo_conf=None, port=None, keep=False,
                 path='Data.fs', blob_dir=None,
                 suicide=True, debug=False, init=True,
                 threaded=False, start_timeout=33, name=None,
                 ):
    """Start a ZeroDB server in a separate process or thread.

    Takes two positional arguments a string containing the storage conf
    and a ZEOConfig object.

    Returns the ZEO address, the test server address, the pid, and the path
    to the config file.
    """

    if not storage_conf:
        storage_conf = '''
        <filestorage>
          path %s
          pack-gc false
        </filestorage>''' % path

    if blob_dir:
        storage_conf = '<blobstorage>\nblob-dir %s\n%s\n</blobstorage>' % (
            blob_dir, storage_conf)

    if zeo_conf is None or isinstance(zeo_conf, dict):
        if port is None:
            raise AssertionError("The port wasn't specified")

        if isinstance(port, int):
            addr = 'localhost', port
        else:
            addr = port

        from ZEO.tests.forker import ZEOConfig
        z = ZEOConfig(addr)
        if zeo_conf:
            z.__dict__.update(zeo_conf)
        zeo_conf = str(z)

        # jam in SSL configuration:
        zeo_conf = zeo_conf.replace('</zeo>', '''
        <ssl>
           certificate {}
           key {}
           authenticate DYNAMIC
        </ssl>
        </zeo>
        '''.format(ZEO.tests.testssl.server_cert,
                   ZEO.tests.testssl.server_key,
                   ))

    # Store the config info in a temp file.
    tmpfile = tempfile.mktemp(".conf", dir=os.getcwd())
    fp = open(tmpfile, 'w')
    fp.write(str(zeo_conf) + '\n\n')
    fp.write(storage_conf)
    fp.close()

    if threaded:
        from threading import Thread
        from six.moves.queue import Queue
    else:
        from multiprocessing import Process as Thread
        from multiprocessing import Queue

    qin = Queue()
    qout = Queue()
    thread = Thread(
        target=runner,
        args=[tmpfile, qin, qout, 999 if suicide else None],
        kwargs=dict(debug=debug, name=name, keep=keep, init=init),
        name = None if name is None else name + '-server-runner',
        )
    thread.daemon = True
    thread.start()
    try:
        addr = qout.get(timeout=start_timeout)
    except Exception:
        whine("SERVER FAILED TO START")
        if thread.is_alive():
            whine("Server thread/process is still running")
        elif not threaded:
            whine("Exit status", thread.exitcode)
        raise

    def stop(stop_timeout=99):
        stop_runner(thread, tmpfile, qin, qout, stop_timeout)

    return addr, stop
