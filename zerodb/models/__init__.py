import persistent
import indexable
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
        indexed_fields = set(filter(lambda key:
                not key.startswith("_") and
                isinstance(getattr(self.__class__, key), indexable.Indexable),
            self.__class__.__dict__.keys()))

        required_fields = set(filter(lambda key: getattr(self.__class__, key).default is None, indexed_fields))

        missed_fields = required_fields.difference(kw)
        if missed_fields:
            raise exceptions.ModelException("You should provide fields: " + ", ".join(map(str, missed_fields)))
