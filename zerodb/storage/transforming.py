from zc.zlibstorage import ZlibStorage
import logging
from zerodb.util.debug import debug_loads


class TransformingStorage(ZlibStorage):
    """
    We'll put encryption in here.
    Also this storge is aware of our loadBulk method
    """

    def __init__(self, *args, **kw):
        self.debug = kw.pop("debug", False)
        self.cipher = kw.pop("cipher", None)
        if self.debug:
            self._debug_download_size = 0
            self._debug_download_count = 0
        super(TransformingStorage, self).__init__(*args, **kw)

        if self.cipher:
            _transform = self._transform
            _untransform = self._untransform
            self._transform = lambda data: self.cipher.encrypt(_transform(data))
            self._untransform = lambda data: _untransform(self.cipher.decrypt(data))

    def load(self, oid, version=''):
        if self.debug:
            if oid not in self._cache.current:
                in_cache = False
            else:
                in_cache = True

        data, serial = self.base.load(oid, version)
        out_data = self._untransform(data)

        if self.debug and not in_cache:
            logging.info("id:%s, type:%s, transform: %s->%s" % (oid.encode("hex"), debug_loads(out_data), len(data), len(out_data)))
            self._debug_download_size += len(data)
            self._debug_download_count += 1

        return out_data, serial

    def loadBulk(self, oids, returns=True):
        if self.debug:
            not_in_cache = set(filter(lambda x: x not in self._cache.current, oids))

        base_result = self.base.loadBulk(oids)
        if returns or self.debug:
            datas, serials = zip(*base_result)
            datas_out = map(self._untransform, datas)
            out = zip(datas_out, serials)
            if self.debug:
                for data, out_data, oid in zip(datas, datas_out, oids):
                    if oid in not_in_cache:
                        logging.info("id:%s, type:%s, transform: %s->%s" % (oid.encode("hex"), debug_loads(out_data), len(data), len(out_data)))
                        self._debug_download_size += len(data)
                if not_in_cache:
                    self._debug_download_count += 1
            if returns:
                return out
