from zerodb.models import Model
from zerodb.models.fields import Field, Text


class Employee(Model):
    name = Field()
    surname = Field()
    description = Text()
    salary = Field()

    def __repr__(self):
        return "<%s %s who earns $%s>" % (self.name, self.surname, self.salary)
