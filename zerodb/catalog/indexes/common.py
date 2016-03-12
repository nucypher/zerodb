import six
from zerodbext.catalog.indexes.common import *

_marker = ()


class CallableDiscriminatorMixin(object):
    """
    Compatibility function which makes index pickleable
    """
    def _init_discriminator(self, discriminator):
        if isinstance(discriminator, tuple):
            self.discriminator, = discriminator
            self.discriminator_callable = True
        else:
            if not isinstance(discriminator, six.string_types):
                raise ValueError('discriminator value must be callable or a '
                                 'string')
            self.discriminator = discriminator
            self.discriminator_callable = False

    def index_doc(self, docid, obj):
        if self.discriminator_callable:
            # Model class definition has a list of virtual fields
            virtuals = getattr(obj.__class__, "_z_virtual_fields", {})
            value = virtuals.get(self.discriminator, _marker)
            if value != _marker:
                try:
                    value = value(obj)
                except:
                    value = _marker
        else:
            value = getattr(obj, self.discriminator, _marker)

        if value is _marker:
            # unindex the previous value
            super(CatalogIndex, self).unindex_doc(docid)

            # Store docid in set of unindexed docids
            self._not_indexed.add(docid)

            return None

        if isinstance(value, Persistent):
            raise ValueError('Catalog cannot index persistent object %s' %
                             value)

        if isinstance(value, Broken):
            raise ValueError('Catalog cannot index broken object %s' %
                             value)

        if docid in self._not_indexed:
            # Remove from set of unindexed docs if it was in there.
            self._not_indexed.remove(docid)

        return super(CatalogIndex, self).index_doc(docid, value)
