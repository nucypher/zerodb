import names
import loremipsum
import transaction
import zerodb
import random
from zerodb.crypto import AES
import models

passphrase = "Much secret so secure wow"

db = zerodb.DB("/tmp/zerosocket", cipher=AES(passphrase))

with transaction.manager:
    for i in xrange(10000):
        e = models.Employee(name=names.get_first_name(),
                            surname=names.get_last_name(),
                            salary=random.randrange(200000),
                            description=loremipsum.get_paragraph(),
                            extra=loremipsum.get_sentence())
        db.add(e)
db.disconnect()
