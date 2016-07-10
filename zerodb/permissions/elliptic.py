"""
Module for auth with elliptic curve cryptography
"""
__module_name__ = "auth_secp256k1_scrypt"

import ecdsa
import hashlib
import scrypt
import struct

from ZEO import auth
from ZEO.auth.base import Client as BaseClient
from ZEO.auth import register_module
from ZEO.Exceptions import AuthError

from . import base
from . import subdb
from zerodb.crypto import rand
from zerodb.crypto import ecc


class ServerStorageMixin(object):
    curve = ecdsa.SECP256k1

    def auth_get_challenge(self):
        """Return realm, challenge, and nonce."""
        self._challenge = rand(32)
        self._key_nonce = self._get_nonce()
        return self.auth_realm, self._challenge, self._key_nonce

    def auth_response(self, resp):
        # verify client response
        username, challenge, resp_sig = resp

        assert self._challenge == challenge

        user = self.database[username]
        verkey = ecc.public(user.pubkey, curve=self.curve)

        h_up = hashlib.sha256(b"%s:%s:%s" % (username.encode(), self.database.realm.encode(), user.pubkey)).digest()

        # regeneration resp from user, password, and nonce
        check = hashlib.sha256(b"%s:%s" % (h_up, challenge)).digest()
        verify = verkey.verify(resp_sig, check)
        if verify:
            self.connection.setSessionKey(base.session_key(h_up, self._key_nonce))
        # This class is per-connection, so we're safe to assign attributes
        authenticated = self._finish_auth(verify)
        if authenticated:
            user_id = self.database.db_root["usernames"][username]
            self.user_id = struct.pack(self.database.uid_pack, user_id)
        return authenticated


class StorageClass(ServerStorageMixin, subdb.StorageClass):
    pass


class Client(BaseClient):
    extensions = ["auth_get_challenge", "auth_response", "get_root_id"]
    curve = ecdsa.SECP256k1

    @classmethod
    def kdf(cls, seed, salt):
        return scrypt.hash(seed, salt)[:cls.curve.baselen]

    def start(self, username, realm, password):
        priv = ecc.private(password, [username, realm], kdf=self.kdf,
                           curve=self.curve)
        _realm, challenge, nonce = self.stub.auth_get_challenge()
        # _realm is str, challenge is 32-byte hash, nonce as well
        if _realm != realm:
            raise AuthError("expected realm %r, got realm %r"
                            % (_realm, realm))
        h_up = hashlib.sha256(b"%s:%s:%s" % (username.encode(), realm.encode(), priv.get_pubkey())).digest()

        check = hashlib.sha256(b"%s:%s" % (h_up, challenge)).digest()
        sig = priv.sign(check)
        result = self.stub.auth_response((username, challenge, sig))
        if result:
            return base.session_key(h_up, nonce)
        else:
            return None


def register_auth():
    if __module_name__ not in auth._auth_modules:
        register_module(__module_name__, StorageClass, Client, base.PermissionsDatabase)
