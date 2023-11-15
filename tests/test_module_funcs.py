import unittest

from pure_interface import *


class IAnimal(Interface):
    species = None

    def speak(self, volume):
        pass

    @property
    def weight(self):
        pass


class ILandAnimal(IAnimal, Interface):
    def num_legs(self):
        pass

    @property
    def height(self):
        pass


class Cat(IAnimal):
    def speak(self, volume):
        pass


class Dog(ILandAnimal):
    def num_legs(self):
        return 4

    @property
    def height(self):
        return 89

    @property
    def weight(self):
        return 6.4

    def speak(self, volume):
        pass


class Mongrel(Dog):
    pass


class Car(object):
    pass


class TestModuleFunctions(unittest.TestCase):
    def test_type_is_interface(self):
        self.assertTrue(type_is_interface(Interface))
        self.assertTrue(type_is_interface(IAnimal))
        self.assertFalse(type_is_interface(object))
        self.assertFalse(type_is_interface(Cat))
        self.assertFalse(type_is_interface(Car))
        self.assertFalse(type_is_interface('hello'))

    def test_get_interface_method_names(self):
        self.assertEqual(get_interface_method_names(IAnimal), {'speak'})
        self.assertEqual(get_interface_method_names(ILandAnimal), {'speak', 'num_legs'})
        self.assertEqual(get_interface_method_names(Cat), set())
        self.assertEqual(get_interface_method_names(Car), set())
        self.assertEqual(get_interface_method_names('hello'), set())

    def test_get_interface_attribute_names(self):
        self.assertEqual(get_interface_attribute_names(IAnimal), {'weight', 'species'})
        self.assertEqual(get_interface_attribute_names(ILandAnimal), {'weight', 'species', 'height'})
        self.assertEqual(get_interface_attribute_names(Cat), set())
        self.assertEqual(get_interface_attribute_names('hello'), set())

    def test_get_interface_names(self):
        self.assertEqual(get_interface_names(IAnimal), {'speak', 'weight', 'species'})
        self.assertEqual(get_interface_names(ILandAnimal), {'speak', 'weight', 'species', 'height', 'num_legs'})
        self.assertEqual(get_interface_names(Cat), set())
        self.assertEqual(get_interface_names('hello'), set())

    def test_get_type_interfaces(self):
        self.assertEqual(get_type_interfaces(IAnimal), [IAnimal])
        self.assertEqual(get_type_interfaces(ILandAnimal), [ILandAnimal, IAnimal])
        self.assertEqual(get_type_interfaces(Cat), [IAnimal])
        self.assertEqual(get_type_interfaces(Dog), [ILandAnimal, IAnimal])
        self.assertEqual(get_type_interfaces(Mongrel), [ILandAnimal, IAnimal])
        self.assertEqual(get_type_interfaces(Car), [])
        self.assertEqual(get_type_interfaces(len), [])
        self.assertEqual(get_type_interfaces('hello'), [])
