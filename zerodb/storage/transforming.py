from zc.zlibstorage import ZlibStorage
import logging
import zope.interface
from zerodb.transform import encrypt, decrypt, compress, decompress
from zerodb.util import encode_hex
from zerodb.util.debug import debug_loads


class TransformingStorage(ZlibStorage):
    """
    Storage which can transform (encrypt and/or compress) data.
    Also this storge is aware of our loadBulk method
    """

    def __init__(self, base, *args, **kw):
        """
        :param base: Storage to transform
        :param bool debug: Output debug log messages
        """
        self.base = base

        self.debug = kw.pop("debug", False)
        if self.debug:
            self._debug_download_size = 0
            self._debug_download_count = 0

        for name in self.copied_methods:
            v = getattr(base, name, None)
            if v is not None:
                setattr(self, name, v)

        zope.interface.directlyProvides(self, zope.interface.providedBy(base))

        base.registerDB(self)

        self._transform = lambda data: encrypt(compress(data), no_cipher_name=True)
        self._transform_named = lambda data: encrypt(compress(data), no_cipher_name=False)
        self._untransform = lambda data: decompress(decrypt(data))

        self._root_oid = None

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
            logging.debug("id:%s, type:%s, transform: %s->%s" % (encode_hex(oid), debug_loads(out_data), len(data), len(out_data)))
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
            logging.debug("Loading: " + ", ".join([encode_hex(oid) for oid in oids]))
            in_cache_before = {oid: oid in self._cache.current for oid in oids}
        base_result = self.base.loadBulk(oids)
        if self.debug:
            in_cache_after = {oid: oid in self._cache.current for oid in oids}
        if returns or self.debug:
            datas, serials = zip(*base_result)
            datas_out = map(self._untransform, datas)
            out = list(zip(datas_out, serials))
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
                                (logline_prefix, encode_hex(oid), debug_loads(out_data), len(data), len(out_data)))
            if returns:
                return out

    def store(self, oid, serial, data, version, transaction):
        if oid == self._root_oid:
            _transform = self._transform_named
        else:
            _transform = self._transform
        return self.base.store(oid, serial, _transform(data), version,
                               transaction)
