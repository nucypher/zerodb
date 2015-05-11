import names
import loremipsum
import transaction
import zerodb
import random
import models

username = "root"
passphrase = "very insecure passphrase - never use it"

db = zerodb.DB("/tmp/zerosocket", username=username, password=passphrase)

with transaction.manager:
    for i in xrange(10000):
        if (i % 100) == 0:
            print i
        e = models.Employee(name=names.get_first_name(),
                            surname=names.get_last_name(),
                            salary=random.randrange(200000),
                            description=loremipsum.get_paragraph(),
                            extra=loremipsum.get_sentence())
        db.add(e)
db.disconnect()
