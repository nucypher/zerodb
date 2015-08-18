import struct
import transaction
from ZEO import auth

import base
import subdb
from elliptic import ServerStorageMixin, Client
from ZEO.Exceptions import StorageError

__module_name__ = "afgh_elliptic_auth"


class StorageClass(ServerStorageMixin, subdb.StorageClass):

    def share_db(self, username, re_key):
        """
        Share whole subdatabase with another user <username> using proxy re-encryption key
        """
        uid = struct.unpack(self.database.uid_pack, self.user_id)[0]
        user2 = self.database[username]
        with transaction.manager:
            if not hasattr(user2, "allowed_dbs"):
                user2.allowed_dbs = self.database.family.IO.BTree()
            user2.allowed_dbs[uid] = re_key

    def unshare_db(self, username, re_key):
        """
        Share whole subdatabase with another user <username> using proxy re-encryption key:
        revoke access
        """
        uid = struct.unpack(self.database.uid_pack, self.user_id)[0]
        user2 = self.database[username]
        if hasattr(user2, "allowed_dbs"):
            with transaction.manager:
                del user2.allowed_dbs[uid]

    def shared_with_me(self):
        uid = struct.unpack(self.database.uid_pack, self.user_id)[0]
        user = self.database.db_root["users"][uid]
        if hasattr(user, "allowed_dbs"):
            return list(user.allowed_dbs.keys())
        else:
            return []

    def get_shared_root_id(self, user):
        this_uid = struct.unpack(self.database.uid_pack, self.user_id)[0]

        if isinstance(user, basestring):
            u = self.database[user]
        elif isinstance(user, (int, long)):
            u = self.database["db_root"][user]
        else:
            raise TypeError("Argument should be string username or int user id")

        if this_uid not in getattr(u, "allowed_dbs", {}):
            raise KeyError("Access denied")

        root = self.storage.load(u.root, '')

        # Now root is encrypted with user's key, need to re-encrypt for us

        return root

    def storea(self, oid, serial, data, id):
        raise NotImplementedError("We implement sharing read-only first")

    def loadEx(self, oid):
        data, tid = super(StorageClass, self).loadEx(oid)
        uid = data[-len(self.user_id):]
        if self.user_id == uid:
            return data[:-len(self.user_id)], tid

        else:
            uid = struct.unpack(self.database.uid_pack, uid)[0]
            if not uid in self.allowed_dbs:
                raise StorageError("Attempt to access encrypted data of others at <%s> by <%s>" % (oid, self.user_id.encode("hex")))
            # To be continued
            # - in-memmory cache of opened proxy re-encryption keys
            # - reencrypt on the fly


def register_auth():
    if __module_name__ not in auth._auth_modules:
        auth.register_module(__module_name__, StorageClass, Client, base.PermissionsDatabase)
