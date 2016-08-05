import argparse
import collections
import pprint
import ZODB
import ZODB.FileStorage

from zerodb.permissions.base import get_admin

parser = argparse.ArgumentParser()
parser.add_argument('path', help="Path to a file-storage file")

def userstats(path):
    result = collections.defaultdict(int)
    for transaction in ZODB.FileStorage.FileIterator(path):
        for record in transaction:
            if record.data:
                result[record.data[-8:]] += (
                    transaction._tend - transaction._tpos + 8)
                break # We only needed one record to get the user.

    storage = ZODB.FileStorage.FileStorage(path, read_only=True)
    db = ZODB.DB(storage)
    with db.transaction() as conn:
        admin = get_admin(conn)
        result = [(uid, admin.users[uid].name, total)
                  for (uid, total) in result.items()
                  ]

    return result

def main():
    pprint(userstats(parser.parse_args().path))
