from setuptools import setup, find_packages

INSTALL_REQUIRES = [
    'setuptools',
    'BTrees',
    'zope.component',
    'ZODB',
    'zope.index',
    'repoze.catalog',
    'zc.zlibstorage',
    'pytest',
    'pycrypto']

setup(
    name="ZeroDB",
    version="0.7",
    packages=find_packages(),
    tests_require=INSTALL_REQUIRES,
    install_requires=INSTALL_REQUIRES,
)
