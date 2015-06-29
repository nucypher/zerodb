from setuptools import setup, find_packages

INSTALL_REQUIRES = [
    'BTrees',
    'zope.component',
    'zodbpickle',
    'ZODB',
    'zope.index',
    'repoze.catalog',
    'zc.zlibstorage',
    'pycrypto',
    'click',
    'flask',
    'requests',
    'jsonpickle',
    'pyelliptic',
    'ecdsa']

setup(
    name="zerodb",
    version="0.91",
    description="End-to-end encrypted database",
    author="ZeroDB Inc.",
    author_email="michael@zerodb.io",
    license="Proprietary",
    url="http://zerodb.io",
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
)
