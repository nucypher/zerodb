from zc.zlibstorage import ZlibStorage
import logging
from zerodb.util.debug import debug_loads


class TransformingStorage(ZlibStorage):
    """
    Storage which can transform (encrypt and/or compress) data.
    Also this storge is aware of our loadBulk method
    """

    def __init__(self, base, *args, **kw):
        """
        :param base: Storage to transform
        :param cipher: Encryptor to use (see zerodb.crypto)
        :param bool debug: Output debug log messages
        """
        self.debug = kw.pop("debug", False)
        self.cipher = kw.pop("cipher", None)
        if self.debug:
            self._debug_download_size = 0
            self._debug_download_count = 0
        super(TransformingStorage, self).__init__(base, *args, **kw)

        if self.cipher:
            _transform = self._transform
            _untransform = self._untransform
            self._transform = lambda data: self.cipher.encrypt(_transform(data))
            self._untransform = lambda data: _untransform(self.cipher.decrypt(data))

    def load(self, oid, version=''):
        """
        Load object by oid

        :param str oid: Object ID
        :param version: Version to load (when we have version control)
        :return: Object and its serial number
        :rtype: tuple
        """
        if self.debug:
            if oid not in self._cache.current:
                in_cache = False
            else:
                in_cache = True

        data, serial = self.base.load(oid, version)
        out_data = self._untransform(data)

        if self.debug and not in_cache:
            logging.debug("id:%s, type:%s, transform: %s->%s" % (oid.encode("hex"), debug_loads(out_data), len(data), len(out_data)))
            self._debug_download_size += len(data)
            self._debug_download_count += 1

        return out_data, serial

    def loadBulk(self, oids, returns=True):
        """
        Load multiple objects at once

        :param list oids: Iterable of oids to load
        :param bool returns: When False, we don't return objects but store them
            in cache
        :return: List of (object, serial) tuples
        :rtype: list
        """
        if self.debug:
            in_cache_before = {oid: oid in self._cache.current for oid in oids}
        base_result = self.base.loadBulk(oids)
        if self.debug:
            in_cache_after = {oid: oid in self._cache.current for oid in oids}
        if returns or self.debug:
            datas, serials = zip(*base_result)
            datas_out = map(self._untransform, datas)
            out = zip(datas_out, serials)
            if self.debug:
                if datas:
                    self._debug_download_count += 1
                for data, out_data, oid in zip(datas, datas_out, oids):
                    logline_prefix = ""
                    if not in_cache_before[oid]:
                        self._debug_download_size += len(data)
                        if not in_cache_after[oid]:
                            self._debug_download_count += 1
                        else:
                            logline_prefix = "(from bulk) "
                        logging.debug("%sid:%s, type:%s, transform: %s->%s" %
                                (logline_prefix, oid.encode("hex"), debug_loads(out_data), len(data), len(out_data)))
            if returns:
                return out
