import zerodb  # ZeroDB itself
import transaction  # Transaction manager
import models  # ..and our data model

# Also we need to generate some random data
import names
import loremipsum
import random

username = "root"
passphrase = "very insecure passphrase - never use it"

db = zerodb.DB(("localhost", 8001), username=username, password=passphrase)

# Everything we record should be within a transaction manager
# or be ended with transaction.commit()
with transaction.manager:
    for i in xrange(10000):
        if (i % 100) == 0:
            # Random text generation is slow, so we report
            # about progress here
            print i
        e = models.Employee(name=names.get_first_name(),
                            surname=names.get_last_name(),
                            salary=random.randrange(200000),
                            description=loremipsum.get_paragraph(),
                            extra=loremipsum.get_sentence())
        db.add(e)  # Don't forget to add created object to the db

    # One special record
    desc = """A theoretical physicist, cosmologist,
author and Director of Research at the Centre for
Theoretical Cosmology within the University of Cambridge,
Stephen William Hawking resides in the United Kingdom."""
    e = models.Employee(name="Stephen", surname="Hawking",
                        salary=400000,
                        description=desc)
    db.add(e)  # Don't forget to add created object to the db

# This is not really necessary
db.disconnect()
