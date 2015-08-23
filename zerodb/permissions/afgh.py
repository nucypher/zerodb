import struct
import transaction
from cachetools import TTLCache
from ZEO import auth

import base
import subdb
# from zerodb.tranform import decrypt
from elliptic import ServerStorageMixin, Client
from ZEO.Exceptions import StorageError
from zerodb.transform.encrypt_afgh import AFGHReEncryption

__module_name__ = "afgh_elliptic_auth"

PRE_CACHE_SIZE = 10000
PRE_CACHE_TTL = 3600

pre_cache = TTLCache(PRE_CACHE_SIZE, PRE_CACHE_TTL)


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

        return self._reencrypt(root, user)

    def storea(self, oid, serial, data, id):
        raise NotImplementedError("We implement sharing read-only first")

    def loadEx(self, oid):
        data, tid = super(StorageClass, self).loadEx(oid)
        uid = data[-len(self.user_id):]
        if self.user_id == uid:
            return data[:-len(self.user_id)], tid

        else:
            return self._reencrypt(data[:-len(self.user_id)], uid), tid

    def _reencrypt(self, data, uid):
        if isinstance(uid, basestring):
            uid = struct.unpack(self.database.uid_pack, uid)[0]
        this_user = self.database.db_root["users"][struct.unpack(self.database.uid_pack, self.user_id)[0]]
        if not uid in this_user.allowed_dbs:
            raise StorageError("Attempt to access encrypted data of others by <%s>" % self.user_id.encode("hex"))

        # Prepare reencryption key
        re_dump = this_user.allowed_dbs[uid]
        re_key = pre_cache.get(re_dump, None)
        if not re_key:
            re_key = AFGHReEncryption(re_dump)
            pre_cache[re_dump] = re_key

        return re_key.reencrypt(data)


def register_auth():
    if __module_name__ not in auth._auth_modules:
        auth.register_module(__module_name__, StorageClass, Client, base.PermissionsDatabase)
