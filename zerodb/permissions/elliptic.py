"""
Module for auth with elliptic curve cryptography
"""

import struct
from ZEO.auth.base import Client as BaseClient
from ZEO.auth import register_module
from ZEO.Exceptions import AuthError

import base
import subdb
from zerodb.crypto import rand, sha256
from zerodb.crypto import ecc


__module_name__ = "ecc_auth"


class StorageClass(subdb.StorageClass):

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
        verkey = ecc.public(user.pubkey)

        h_up = sha256("%s:%s:%s" % (username, self.database.realm, user.pubkey))

        # regeneration resp from user, password, and nonce
        check = sha256("%s:%s" % (h_up, challenge))
        verify = verkey.verify(resp_sig, check)
        if verify:
            self.connection.setSessionKey(base.session_key(h_up, self._key_nonce))
        # This class is per-connection, so we're safe to assign attributes
        authenticated = self._finish_auth(verify)
        if authenticated:
            user_id = self.database.db_root["usernames"][username]
            self.user_id = struct.pack(self.database.uid_pack, user_id)
        return authenticated

    extensions = [auth_get_challenge, auth_response] + subdb.StorageClass.extensions


class Client(BaseClient):
    extensions = ["auth_get_challenge", "auth_response", "get_root_id"]

    def start(self, username, realm, password):
        priv = ecc.private(password)
        _realm, challenge, nonce = self.stub.auth_get_challenge()
        # _realm is str, challenge is 32-byte hash, nonce as well
        if _realm != realm:
            raise AuthError("expected realm %r, got realm %r"
                            % (_realm, realm))
        h_up = sha256("%s:%s:%s" % (username, realm, priv.get_pubkey()))

        check = sha256("%s:%s" % (h_up, challenge))
        sig = priv.sign(check)
        result = self.stub.auth_response((username, challenge, sig))
        if result:
            return base.session_key(h_up, nonce)
        else:
            return None


def register_auth():
    register_module(__module_name__, StorageClass, Client, base.PermissionsDatabase)
