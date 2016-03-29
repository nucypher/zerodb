import sys
import os
import subprocess
import errno
import tempfile

from distutils import ccompiler, log
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
    cc.include_dirs = [str(x) for x in include_dirs] # PY2

    with tempfile.NamedTemporaryFile(mode="wt", suffix=".c") as f:
        f.write('#include "ffi.h"\nvoid f(){}\n')
        f.flush()
        try:
            cc.compile([f.name])
            return True;
        except ccompiler.CompileError:
            return False


def have_cffi():
    try:
        import cffi
        return True
    except ImportError:
        return False


# If we have neither cffi nor ffi.h we fall back to pycryptodome.
# Note that the warning is only visible if pip is run with -v.

if have_cffi() or can_build_cffi():
    INSTALL_REQUIRES.append("aes256gcm-nacl")
else:
    log.warn("warning: ffi.h not found: aes256gcm-nacl optimization disabled")


setup(
    name="zerodb",
    version="0.97.3",
    description="End-to-end encrypted database",
    author="ZeroDB Inc.",
    author_email="michael@zerodb.io",
    license="AGPLv3",
    url="http://zerodb.io",
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
)
