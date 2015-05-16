#!/usr/bin/env python2

from zerodb.crypto import ecc

passphrase = raw_input("Enter your passphrase: ")
key = ecc.private(passphrase)
print "Your hex public key:", key.get_pubkey().encode("hex")
