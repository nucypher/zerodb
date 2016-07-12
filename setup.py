import sys
import os
import platform
import subprocess
import errno
import tempfile

from distutils import ccompiler, log
from setuptools import setup, find_packages

INSTALL_REQUIRES = [
    'BTrees',
    'zope.component>=4.0.0',
    'zodbpickle',
    'ZODB>=4.0.0',
    'zope.index>=4.0.0',
    'zerodbext.catalog==0.8.4',
    'cachetools',
    'zc.zlibstorage',
    'flask-cors',
    'flask>=0.10',
    'requests>=2.0',
    'jsonpickle',
    'ecdsa>=0.10',
    'zope.event>=4.0.0',
    'zope.lifecycleevent>=4.0.0',
    'six>=1.7.0',
    'scrypt'
]

TESTS_REQUIRE = [
    'pytest',
    'coverage',
    'path.py',
    'mock',
    'wheel',
    'pytest-cov',
    'pdbpp'
]


# The following is to avoid build errors on brand new Amazon Ubuntu
# instances which may not have libffi-dev installed.

# Function copied from cffi 1.5.2
def _ask_pkg_config(resultlist, option, result_prefix='', sysroot=False):
    pkg_config = os.environ.get('PKG_CONFIG', 'pkg-config')
    try:
        p = subprocess.Popen([pkg_config, option, 'libffi'], stdout=subprocess.PIPE)
    except OSError as e:
        if e.errno not in [errno.ENOENT, errno.EACCES]:
            raise
    else:
        t = p.stdout.read().decode().strip()
        p.stdout.close()
        if p.wait() == 0:
            res = t.split()
            res = [x[len(result_prefix):] for x in res if x.startswith(result_prefix)]
            sysroot = sysroot and os.environ.get('PKG_CONFIG_SYSROOT_DIR', '')
            if sysroot:
                # old versions of pkg-config don't support this env var,
                # so here we emulate its effect if needed
                res = [x if x.startswith(sysroot) else sysroot + x for x in res]
            resultlist[:] = res


def can_build_cffi():
    # Windows hopefully grabs binary wheels
    if sys.platform == "win32":
        return True

    # Include dirs copied from cffi 1.5.2
    include_dirs = ["/usr/include/ffi", "/usr/include/libffi"]
    _ask_pkg_config(include_dirs, "--cflags-only-I", "-I", sysroot=True)

    if "freebsd" in sys.platform:
        include_dirs.append("/usr/local/include")

    cc = ccompiler.new_compiler()
    cc.include_dirs = [str(x) for x in include_dirs]  # PY2

    with tempfile.NamedTemporaryFile(mode="wt", suffix=".c") as f:
        f.write('#include "ffi.h"\nvoid f(){}\n')
        f.flush()
        try:
            cc.compile([f.name])
            return True
        except ccompiler.CompileError:
            return False


# If we don't have ffi.h we fall back to pycryptodome.
# Note that the warning is only visible if pip is run with -v.


def have_pycrypto():
    try:
        import Crypto
        return True
    except ImportError:
        return False


def have_pycryptodome():
    try:
        from Crypto.Cipher.AES import MODE_GCM
        return True
    except ImportError:
        return False


def have_aesni():
    if have_pycryptodome():
        from Crypto.Cipher.AES import _raw_aesni_lib
        return _raw_aesni_lib is not None

    else:
        try:
            with open("/proc/cpuinfo", "r") as f:
                info = f.read()
        except IOError:
            info = None

        if (info is None) or ("aes" in info):
            # If we have a platform w/o cpuinfo, assume we have AESNI
            # Perhaps, should call sysctl in OSX
            return True
        else:
            return False


def have_sodium_wheel():
    return (platform.system() == "Darwin") and (platform.mac_ver()[0].startswith("10.10"))


if platform.python_implementation() == "PyPy":
    INSTALL_REQUIRES.append('ZEO>=4.2.0b1')
else:
    INSTALL_REQUIRES.append('ZEO>=4.0.0')


if have_aesni():
    if have_sodium_wheel() or can_build_cffi():
        INSTALL_REQUIRES.append("aes256gcm-nacl")
        if have_pycrypto() and not have_pycryptodome():
            INSTALL_REQUIRES.append("pycrypto")
        else:
            INSTALL_REQUIRES.append("pycryptodome")

    else:
        INSTALL_REQUIRES.append("pycryptodome")
        log.warn("WARNING: ffi.h not found: aes256gcm-nacl optimization disabled")

else:
    INSTALL_REQUIRES.append("pycryptodome")


setup(
    name="zerodb",
    version="0.98.0",
    description="End-to-end encrypted database",
    author="ZeroDB Inc.",
    author_email="michael@zerodb.io",
    license="AGPLv3",
    url="http://zerodb.io",
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
    extras_require={'testing': TESTS_REQUIRE},
)
