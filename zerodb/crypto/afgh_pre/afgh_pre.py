import jpype
import os
import struct

from array import array
from os.path import dirname, abspath


def start_jvm():
    jvm_path = jpype.getDefaultJVMPath()
    jars_path = os.path.join(dirname(abspath(__file__)), "jars")
    load_modules = ["commons-codec-1.6", "jpbc-plaf-1.2.0", "jpbc-api-1.2.0", "nics-crypto"]
    load_modules = [os.path.join(jars_path, x) + ".jar" for x in load_modules]
    jpype.startJVM(jvm_path, "-Djava.class.path=" + ":".join(load_modules))


AFGHGlobalParameters = AFGHProxyReEncryption = CurveElement = GTFiniteElement = None
Tuple = String = params = None


def init():
    global AFGHGlobalParameters, AFGHProxyReEncryption, CurveElement, GTFiniteElement
    global Tuple, String, params

    start_jvm()
    AFGHGlobalParameters = jpype.JClass("nics.crypto.proxy.afgh.AFGHGlobalParameters")
    AFGHProxyReEncryption = jpype.JClass("nics.crypto.proxy.afgh.AFGHProxyReEncryption")
    CurveElement = jpype.JClass("it.unisa.dia.gas.plaf.jpbc.field.curve.CurveElement")
    GTFiniteElement = jpype.JClass("it.unisa.dia.gas.plaf.jpbc.field.gt.GTFiniteElement")
    Tuple = jpype.JClass("nics.crypto.Tuple")
    String = jpype.java.lang.String
    params = AFGHGlobalParameters(256, 1536)


init()


def load_priv(s):
    Zq = params.getZq()
    return Zq.newElement(jpype.java.math.BigInteger(array("b", s)))


def dump_priv(priv):
    return array("b", jpype.java.math.BigInteger.toByteArray(priv.toBigInteger())).tostring()


def load_pub(s):
    """Works for both public and re-encryption keys"""
    el = CurveElement(params.getG1())
    el.setFromBytesCompressed(array("b", s))
    return el


def dump_pub(pub):
    return array("b", pub.toBytesCompressed()).tostring()


def dump_gtf(el):
    return array("b", el.toBytes()).tostring()


def load_gtf(m):
    x = GTFiniteElement(params.getZ()).duplicate()
    b = array("b", m)
    x.setFromBytes(b)
    return x


def dump_re_message(m):
    return dump_gtf(m.get(1)) + dump_gtf(m.get(2))


def load_re_message(m):
    x1 = load_gtf(m[:len(m) / 2])
    x2 = load_gtf(m[len(m) / 2:])
    return Tuple([x1, x2])


def dump_e_message(m):
    x1 = dump_pub(m.get(1))
    x2 = dump_gtf(m.get(2))
    fmt = struct.pack("HH", len(x1), len(x2))
    return fmt + x1 + x2


def load_e_message(m):
    l1, l2 = struct.unpack("HH", m[:4])
    x1 = load_pub(m[4:(4 + l1)])
    x2 = load_gtf(m[(4 + l1):])
    return Tuple([x1, x2])


class Key(object):
    def __init__(self, priv=None, pub=None):
        """
        :param str dump: Load private key from dump
        If there is no dump, will be generated
        """
        self.priv = priv
        self.pub = pub

        if self.priv:
            priv_inv = priv.duplicate()
            self.priv_invert = priv_inv.invert()

        if self.pub:
            self.pub_pow = self.pub.pow()

    @classmethod
    def load_priv(cls, s, generate_pub=True):
        priv = load_priv(s)

        if generate_pub:
            pub = AFGHProxyReEncryption.generatePublicKey(priv, params)
        else:
            pub = None

        return cls(priv=priv, pub=pub)

    def dump_priv(self):
        return dump_priv(self.priv)

    def dump_pub(self):
        return dump_pub(self.pub)

    @classmethod
    def make_priv(cls, generate_pub=True):
        priv = AFGHProxyReEncryption.generateSecretKey(params)

        if generate_pub:
            pub = AFGHProxyReEncryption.generatePublicKey(priv, params)
        else:
            pub = None

        return cls(priv=priv, pub=pub)

    @classmethod
    def load_pub(cls, s):
        return cls(pub=load_pub(s))

    def encrypt(self, message):
        e = AFGHProxyReEncryption.bytesToElement(array("b", message), params.getG2())
        c_a = AFGHProxyReEncryption.secondLevelEncryption(e, self.pub_pow, params)
        return dump_e_message(c_a)

    def decrypt_my(self, s):
        c_a = load_e_message(s)
        m = AFGHProxyReEncryption.secondLevelDecryption(c_a, self.priv, params)
        return array("b", m.toBytes()).tostring().strip("\x00")

    def decrypt_re(self, s):
        c_b = load_re_message(s)
        m = AFGHProxyReEncryption.firstLevelDecryptionPreProcessing(c_b, self.priv_invert, params)
        return array("b", m.toBytes()).tostring().strip("\x00")

    def re_key(self, pub):
        if isinstance(pub, Key):
            pub = pub.pub
        elif isinstance(pub, basestring):
            pub = load_pub(pub)
        return ReKey.make(self.priv, pub)


class ReKey(object):
    def __init__(self, key):
        self.key = key
        self.key_ppp = params.getE().pairing(key)

    @classmethod
    def make(cls, priv, pub):
        if isinstance(priv, Key):
            priv = priv.priv
        if isinstance(pub, Key):
            pub = pub.pub
        key = AFGHProxyReEncryption.generateReEncryptionKey(pub, priv)
        return cls(key)

    def dump(self):
        return dump_pub(self.key)

    @classmethod
    def load(cls, s):
        return cls(load_pub(s))

    def reencrypt(self, m):
        c_b = AFGHProxyReEncryption.reEncryption(load_e_message(m), self.key, self.key_ppp)

        return dump_re_message(c_b)


if __name__ == "__main__":
    pass
