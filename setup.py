from setuptools import setup, find_packages

INSTALL_REQUIRES = [
    'BTrees',
    'zope.component',
    'zodbpickle',
    'ZODB',
    'zope.index',
    'repoze.catalog',
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
    'aes256gcm-nacl']

setup(
    name="zerodb",
    version="0.96.21",
    description="End-to-end encrypted database",
    author="ZeroDB Inc.",
    author_email="michael@zerodb.io",
    license="AGPLv3",
    url="http://zerodb.io",
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
)
