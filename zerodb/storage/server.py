import socket
import ssl
import logging

from errno import EWOULDBLOCK, ECONNABORTED, EAGAIN, ENOTCONN, EBADF
from asyncore import _DISCONNECTED

from ZEO.zrpc.server import Dispatcher as BaseDispatcher
from ZEO.zrpc.server import log
from ZEO.zrpc.connection import Connection


class SSLDispatcher(BaseDispatcher):
    ssl_context_info = None
    ssl_context = None

    def __init__(self, addr, factory=Connection, map=None, ssl_context=None):
        if ssl_context is not None:
            self.ssl_context_info = ssl_context
        if isinstance(self.ssl_context_info, tuple):
            self.create_ssl_context(*self.ssl_context_info)
        BaseDispatcher.__init__(self, addr, factory, map)

    def create_ssl_context(self, certfile, keyfile=None):
        self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        log('loading certificate %s' % certfile, logging.INFO)
        self.ssl_context.load_cert_chain(certfile, keyfile)

    def create_socket(self, family, type):
        self.family_and_type = family, type
        sock = socket.socket(family, type)
        if self.ssl_context is not None:
            sock = self.ssl_context.wrap_socket(sock, server_side=True)
        sock.setblocking(0)
        self.set_socket(sock)

    def accept(self):
        try:
            conn, addr = self.socket.accept()
        except TypeError:
            return None
        except socket.error as why:
            if why.args[0] in (EWOULDBLOCK, ECONNABORTED, EAGAIN):
                return None
            else:
                raise
        else:
            return conn, addr

    def send(self, data):
        try:
            result = self.socket.send(data)
            return result
        except socket.error, why:
            if why.args[0] == EWOULDBLOCK:
                return 0
            elif why.args[0] in _DISCONNECTED:
                self.handle_close()
                return 0
            else:
                raise

    def recv(self, buffer_size):
        try:
            data = self.socket.recv(buffer_size)
            if not data:
                # a closed connection is indicated by signaling
                # a read condition, and having recv() return 0.
                self.handle_close()
                return ''
            else:
                return data
        except socket.error, why:
            if why.args[0] in _DISCONNECTED:
                self.handle_close()
                return ''
            else:
                raise

    def close(self):
        self.connected = False
        self.accepting = False
        self.connecting = False
        self.del_channel()
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except socket.error, why:
            if why.args[0] not in (ENOTCONN, EBADF):
                raise

