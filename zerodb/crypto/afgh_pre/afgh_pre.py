import jpype
import os

from os.path import dirname, abspath


def start_jvm():
    jvm_path = jpype.getDefaultJVMPath()
    jars_path = os.path.join(dirname(abspath(__file__)), "jars")
    load_modules = ["commons-codec-1.6", "jpbc-plaf-1.2.0", "jpbc-api-1.2.0", "nics-crypto"]
    load_modules = [os.path.join(jars_path, x) + ".jar" for x in load_modules]
    jpype.startJVM(jvm_path, "-Djava.class.path=" + ":".join(load_modules))


# When doing multi-processing, need to start again
# Multitreading-friendly
start_jvm()


AFGHGlobalParameters = jpype.JClass("nics.crypto.proxy.afgh.AFGHGlobalParameters")
AFGHProxyReEncryption = jpype.JClass("nics.crypto.proxy.afgh.AFGHProxyReEncryption")
CurveElement = jpype.JClass("it.unisa.dia.gas.plaf.jpbc.field.curve.CurveElement")
GTFiniteElement = jpype.JClass("it.unisa.dia.gas.plaf.jpbc.field.gt.GTFiniteElement")
Tuple = jpype.JClass("nics.crypto.Tuple")
String = jpype.java.lang.String


params = AFGHGlobalParameters(256, 1536)
