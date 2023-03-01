import abc
import unittest

import pure_interface


class SomeOtherMetaClass(pure_interface.InterfaceType):
    def __new__(mcs, name, bases, clsdict):
        cls = pure_interface.InterfaceType.__new__(mcs, name, bases, clsdict)
        return cls


class InnocentBystander(metaclass=SomeOtherMetaClass):
    def method(self):
        pass


class InnocentBystanderWithABC(metaclass=SomeOtherMetaClass):
    @abc.abstractmethod
    def method(self):
        pass

    @property
    @abc.abstractmethod
    def prop(self):
        pass


class ABCImpl(InnocentBystanderWithABC):
    def __init__(self):
        self.prop = 3

    def method(self):
        pass


class MyInterface(pure_interface.Interface):
    def method2(self):
        pass


class SubclassWithInterface(InnocentBystander, MyInterface):
    def method(self):
        pass


class SubSubclassWithInterface(SubclassWithInterface):
    def foo(self):
        pass


class SubSubSubclassWithInterface(SubSubclassWithInterface):
    def bar(self):
        pass


class TestMetaClassMixingChecks(unittest.TestCase):
    def test_submeta_class(self):
        try:
            innocent_bystander = InnocentBystander()
            innocent_bystander.method()
        except Exception as exc:
            self.fail('No exception expected. Got\n' + str(exc))

    def test_submeta_class_with_interface(self):
        with self.assertRaises(TypeError):
            SubclassWithInterface()

    def test_bystander(self):
        # check that property patching is not done to classes that do not inherit an interface
        with self.assertRaises(TypeError):
            ABCImpl()

    def test_dir_subclass(self):
        listing = dir(SubclassWithInterface)
        self.assertIn('method2', listing)
        self.assertIn('method', listing)

    def test_dir_subsubclass(self):
        listing = dir(SubSubclassWithInterface)
        self.assertIn('method2', listing)
        self.assertIn('method', listing)
        self.assertIn('foo', listing)

    def test_dir_subsubsubclass(self):
        listing = dir(SubSubSubclassWithInterface)
        self.assertIn('method2', listing)
        self.assertIn('method', listing)
        self.assertIn('foo', listing)
        self.assertIn('bar', listing)
