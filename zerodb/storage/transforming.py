from zc.zlibstorage import ZlibStorage
from ZODB.utils import maxtid
import logging
import zope.component
import zope.interface
from zerodb.transform import encrypt, decrypt, compress, decompress
from zerodb.transform import get_encryption_signature
from zerodb.util import encode_hex
from zerodb.util.debug import debug_loads
import zerodb.transform.interfaces

_gsm = zope.component.getGlobalSiteManager()

class TransformingStorage(ZlibStorage):
    """
    Storage which can transform (encrypt and/or compress) data.
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

        self._root_oid = base.get_root_id()

        # configure default encrytion based on root encryption:
        data = base.loadBefore(self._root_oid, maxtid)[0]
        sig = get_encryption_signature(data)
        if sig:
            _gsm.registerUtility(
                _gsm.getUtility(
                    zerodb.transform.interfaces.IEncrypter,
                    sig.decode(),
                    )
                )

    def loadBefore(self, oid, tid):
        """Load last state for a given oid before a given tid

        :param str oid: Object ID
        :param str tid: Transaction timestamp
        :return: Object and its serial number and following serial number
        :rtype: tuple
        """
        if self.debug:
            if oid not in self._cache.current:
                in_cache = False
            else:
                in_cache = True

        data, serial, tend = self.base.loadBefore(oid, tid)
        out_data = self._untransform(data)

        if self.debug and not in_cache:
            logging.debug(
                "id:%s, type:%s, transform: %s->%s" % (
                    encode_hex(oid),
                    debug_loads(out_data),
                    len(data),
                    len(out_data),
                    ))
            self._debug_download_size += len(data)
            self._debug_download_count += 1

        return out_data, serial, tend

    def store(self, oid, serial, data, version, transaction):
        if oid == self._root_oid:
            _transform = self._transform_named
        else:
            _transform = self._transform
        return self.base.store(oid, serial, _transform(data), version,
                               transaction)
