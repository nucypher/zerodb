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
    'aes256gcm-nacl',
    'ZEO',
    'six'
]

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
