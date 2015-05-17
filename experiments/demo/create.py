import zerodb  # ZeroDB itself
import transaction  # Transaction manager
import models  # ..and our data model

# Also we need to generate some random data
import names
import loremipsum
import random

username = "root"
passphrase = "very insecure passphrase - never use it"

db = zerodb.DB("/tmp/zerosocket", username=username, password=passphrase)

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
    desc = """The 44th president of the United States,\\
author and the most popular person in the world,\\
Barack Hussein Obama II, has an estimated net worth of\\
$12.2 million. Excluding the $1.4 million in Nobel Prize\\
money he donated to charity and his primary home."""
    e = models.Employee(name="Barack", surname="Obama",
                        salary=400000,
                        description=desc)
    db.add(e)  # Don't forget to add created object to the db

# This is not really necessary
db.disconnect()
