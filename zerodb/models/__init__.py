import persistent
import fields
import exceptions


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

    def __init__(self, **kw):
        # This set will go to metaclass
        indexed_fields = set(filter(lambda key:
                not key.startswith("_") and
                isinstance(getattr(self.__class__, key), fields.Indexable),
            self.__class__.__dict__.keys()))

        # This set will go to metaclass
        required_fields = set(filter(lambda key: getattr(self.__class__, key).default is None, indexed_fields))

        # Indexed fields which have default values
        default_fields = indexed_fields.difference(required_fields).difference(kw)

        missed_fields = required_fields.difference(kw)
        if missed_fields:
            raise exceptions.ModelException("You should provide fields: " + ", ".join(map(str, missed_fields)))

        for field in default_fields:
            default = getattr(self.__class__, field).default
            if callable(default):
                default = default()
            setattr(self, field, default)

        for field, value in kw.iteritems():
            setattr(self, field, value)
