import persistent
import fields
import exceptions
from zerodb.intid import IdStore
from zerodb.trees import family32
from zerodb.catalog import Catalog
from zerodb.models.fields import Field, Text


class ModelMeta(type):
    def __init__(cls, name, bases, dct):
        if bases != (persistent.Persistent,):  # Only subclasses of Model can do it, not Model itself
            used_fields = set(filter(lambda key:
                    not key.startswith("_") and
                    isinstance(dct[key], fields.Indexable),
                dct.keys()))

            required_fields = set(filter(lambda key: dct[key].default is None, used_fields))
            virtual_fields = {key: dct[key].virtual for key in used_fields
                    if dct[key].virtual is not None}

            default_fields = used_fields - required_fields

            cls._z_indexed_fields = set(filter(lambda key: dct[key].indexed, used_fields))
            cls._z_default_fields = default_fields.difference(virtual_fields)
            cls._z_virtual_fields = virtual_fields
            cls._z_required_fields = required_fields.difference(virtual_fields)

            cls.__modelname__ = cls.__modelname__ or name.lower()

            # Clean up all the fields we've used
            dct = {k: dct[k] for k in dct.keys() if k not in used_fields}

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

    # TODO we should (?) provide some way to save model definition into the database
    # and generate model class from there.
    # This could be valuable when working with json which doesn't keep any python code
    # Or we should make a method which allows to generate a new model from json

    __metaclass__ = ModelMeta
    __modelname__ = None
    __family__ = family32

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

    @classmethod
    def create_store(cls):
        """Returns intid.IdStore storage for this class"""
        return IdStore(family=cls.__family__)

    @classmethod
    def create_catalog(cls):
        """Creates and returns catalog for this model with indexes in it"""
        catalog = Catalog()  # TODO: specify family as a parameter
        for name in cls._z_indexed_fields:
            field = getattr(cls, name)

            if field.virtual:
                # Tuple discriminator means virtual field.
                # Index has to look it up in model._z_virtual_fields,
                # where model = obj.__class__
                discriminator = (name,)
            else:
                discriminator = None

            catalog[name] = field.Index(discriminator or name)
        return catalog
