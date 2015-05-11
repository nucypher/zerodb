import zerodb
from zerodb.catalog.query import *
from models import Employee

PASSPHRASE = "very insecure passphrase - never use it"
# SOCKET = ("ec2-52-10-134-79.us-west-2.compute.amazonaws.com", 3000)  # or "/tmp/zerosocket"
SOCKET = "/tmp/zerosocket"

db = zerodb.DB(SOCKET, username="root", password=PASSPHRASE)
print len(db[Employee])

johns = db[Employee].query(name="John", limit=10)
print len(johns)
print johns

rich_johns = db[Employee].query(InRange("salary", 195000, 200000), name="John")
print len(rich_johns)
print rich_johns

presidents = db[Employee].query(Contains("description", "president of United States"))
print len(presidents)
if presidents:
    print presidents[0]
    print presidents[0].description
