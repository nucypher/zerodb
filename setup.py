from setuptools import setup, find_packages

INSTALL_REQUIRES = [
    'BTrees',
    'zope.component',
    'zodbpickle',
    'ZODB',
    'zope.index',
    'repoze.catalog',
    'lz4',
    'zc.zlibstorage',
    'pycrypto',
    'click',
    'flask-cors',
    'flask',
    'requests',
    'jsonpickle',
    'JPype1',
    'pyelliptic',
    'cachetools',
    'ecdsa']

setup(
    name="zerodb",
    version="0.91.1",
    description="End-to-end encrypted database",
    author="ZeroDB Inc.",
    author_email="michael@zerodb.io",
    license="Proprietary",
    url="http://zerodb.io",
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
)
