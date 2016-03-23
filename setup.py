from os.path import isdir, isfile, join
from distutils import log

from setuptools import setup, find_packages

INSTALL_REQUIRES = [
    'BTrees',
    'zope.component',
    'zodbpickle',
    'ZODB',
    'zope.index',
    'zerodbext.catalog',
    'cachetools',
    'zc.zlibstorage',
    'pycryptodome',
    'flask-cors',
    'flask',
    'requests',
    'jsonpickle',
    'pyelliptic',
    'ecdsa',
    'zope.event',
    'zope.lifecycleevent',
    'ZEO',
    'six'
]


# This is to avoid build errors on brand new Amazon Ubuntu instances
# which may not have libffi-dev installed.
#
# If we have neither cffi nor ffi.h we fall back to pycryptodome.
# Note that the warning is only visible if pip is run with -v.

def have_cffi():
    try:
        import cffi
    except ImportError:
        return False
    else:
        return True

def have_ffi_h():
    include_dirs = ["/usr/include", "/usr/local/include"]
    for dir in include_dirs:
        if isdir(dir):
            if isfile(join(dir, "ffi.h")) or isfile(join(dir, "ffi", "ffi.h")):
                return True
    return False

if have_cffi() or have_ffi_h():
    INSTALL_REQUIRES.append("aes256gcm-nacl")
else:
    log.warn("warning: *** ffi.h not found - aes256gcm-nacl optimization disabled ***")
    INSTALL_REQUIRES.append("pycryptodome")


setup(
    name="zerodb",
    version="0.97.2.1",
    description="End-to-end encrypted database",
    author="ZeroDB Inc.",
    author_email="michael@zerodb.io",
    license="AGPLv3",
    url="http://zerodb.io",
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
)
