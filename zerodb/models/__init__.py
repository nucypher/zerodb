import persistent
import fields
import exceptions


class ModelMeta(type):
    def __init__(cls, name, bases, dct):
        if bases != (persistent.Persistent,):  # Only subclasses of Model can do it, not Model itself
            indexed_fields = set(filter(lambda key:
                    not key.startswith("_") and
                    isinstance(dct[key], fields.Indexable),
                dct.keys()))

            required_fields = set(filter(lambda key: dct[key].default is None, indexed_fields))

            default_fields = indexed_fields.difference(required_fields)

            cls._z_indexed_fields = indexed_fields
            cls._z_required_fields = required_fields
            cls._z_default_fields = default_fields

            cls.__modelname__ = cls.__modelname__ or name.lower()

        super(ModelMeta, cls).__init__(name, bases, dct)


class Model(persistent.Persistent):
    """
    Data model to easily create indexable persistent objects.
    If an object declares a property from indexable, this property is indexed.
    *All* other properties are stored but unindexed

    Example:
        >>> class Page(Model):
        ...     title = indexable.Field()
        ...     text = indexable.Text()

        ... page = Page(title="Hello", text="World", extra=12345)
    """
    __metaclass__ = ModelMeta
    __modelname__ = None

    def __init__(self, **kw):
        missed_fields = self._z_required_fields.difference(kw)
        if missed_fields:
            raise exceptions.ModelException("You should provide fields: " + ", ".join(map(str, missed_fields)))

        for field in self._z_default_fields.difference(kw):
            default = getattr(self.__class__, field).default
            if callable(default):
                default = default()
            setattr(self, field, default)

        for field, value in kw.iteritems():
            setattr(self, field, value)
