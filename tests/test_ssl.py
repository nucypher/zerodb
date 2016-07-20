"""Test new SSL-based access
"""

import zerodb
import ZEO
import ZEO.tests.testssl

def test_basic():
    # zerodb.server took care of setting up a databasw with a root
    # user and starting a server for it.  The root user's cert is from
    # ZEO.testing.  The server is using a server cert from ZEO.tests.
    addr, stop = zerodb.server()

    # Create an admin client.  Admin data aren't encrypted, so we use
    # a regular ZEO client.
    admin = ZEO.client(addr, ssl = ZEO.tests.testssl.client_ssl())









    admin.close()
    stop()
