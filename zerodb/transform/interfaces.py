from zope.interface import Attribute, Interface


class ICompressor(Interface):
    """Compressing or decompressing data"""
    name = Attribute("Signature that object is compressed with this algorithm. Recorded as '.cname$'")
    _compress = Attribute("Low-level compress function")
    _decompress = Attribute("Low-level decompress function")

    def compress(data):
        """Compresses data"""

    def decompress(data):
        """Decompresses data"""

    def register(default):
        """Register utility"""


class IEncrypter(Interface):
    """Encrypting or decrypting data"""
    name = Attribute("Signature that object is encrypted with this algorithm. Recorded as '.ename$'")
    attributes = Attribute("List of attributes to consume from init")

    def encrypt(data):
        """Encrypts data"""

    def decrypt(data):
        """Decrypts data"""
