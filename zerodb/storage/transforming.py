from zc.zlibstorage import ZlibStorage


class TransformingStorage(ZlibStorage):
    """
    We'll put encryption in here.
    Also this storge is aware of our loadBulk method
    """

    def loadBulk(self, oids, returns=True):
        base_result = self.base.loadBulk(oids)
        if returns:
            datas, serials = zip(*base_result)
            return zip(map(self._untransform, datas), serials)
