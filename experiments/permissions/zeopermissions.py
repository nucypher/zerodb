"""
StorageServer which provides granular access to zodb based on auth info
"""

# from ZEO.StorageServer import ZEOStorage, StorageServer
from ZEO.auth.auth_digest import StorageClass as AuthStorageClass
from ZEO.auth import register_module
from ZEO.auth.auth_digest import DigestClient
from ZEO.auth.auth_digest import DigestDatabase
import logging

log = logging.getLogger(__name__)


class PermittableZEOStorage(AuthStorageClass):

    def _check_permission(self, name, oid):
        print name, oid.encode("hex"), getattr(self, "username", None)
        return True

    def auth_response(self, resp):
        """
        Record username to the connection.
        We need to know it to figure out who reads what
        """

        result = AuthStorageClass.auth_response(self, resp)

        username = resp[0] if self.authenticated else None
        self.username = username

        return result

    # methods
    # loadEx, loadBefore, deleteObject, storea, restorea, storeBlobEnd, storeBlobShared, sendBlob, loadSerial?
    # get_info shoud show auth support
    # need get_private_root and get_public_root
    # store with permissions, e.g. obj -> struct.pack("Q", user_id) + data -> xdata[:8] + xdata[8:]

    def loadEx(self, oid):
        if self._check_permission("loadEx", oid):
            return AuthStorageClass.loadEx(self, oid)

    def storea(self, oid, serial, data, id):
        if self._check_permission("storea", oid):
            return AuthStorageClass.storea(self, oid, serial, data, id)


def register_auth():
    register_module("permidigest", PermittableZEOStorage, DigestClient, DigestDatabase)
