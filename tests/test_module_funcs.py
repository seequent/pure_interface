# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


import unittest

from pure_interface import *


class IAnimal(PureInterface):
    def speak(self, volume):
        pass

    @property
    def weight(self):
        pass


class ILandAnimal(IAnimal):
    def num_legs(self):
        pass

    @property
    def height(self):
        pass


class Cat(Concrete, IAnimal):
    def speak(self, volume):
        pass


class Dog(Concrete, ILandAnimal):
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
    def test_type_is_pure_interface(self):
        self.assertTrue(type_is_pure_interface(PureInterface))
        self.assertTrue(type_is_pure_interface(IAnimal))
        self.assertFalse(type_is_pure_interface(object))
        self.assertFalse(type_is_pure_interface(Cat))
        self.assertFalse(type_is_pure_interface(Car))
        self.assertFalse(type_is_pure_interface('hello'))

    def test_get_interface_method_names(self):
        self.assertEqual(get_interface_method_names(IAnimal), {'speak'})
        self.assertEqual(get_interface_method_names(ILandAnimal), {'speak', 'num_legs'})
        self.assertEqual(get_interface_method_names(Cat), set())
        self.assertEqual(get_interface_method_names(Car), set())
        self.assertEqual(get_interface_method_names('hello'), set())

    def test_get_interface_property_names(self):
        self.assertEqual(get_interface_property_names(IAnimal), {'weight'})
        self.assertEqual(get_interface_property_names(ILandAnimal), {'weight', 'height'})
        self.assertEqual(get_interface_property_names(Cat), set())
        self.assertEqual(get_interface_property_names('hello'), set())

    def test_get_type_interfaces(self):
        self.assertEqual(get_type_interfaces(IAnimal), [IAnimal])
        self.assertEqual(get_type_interfaces(ILandAnimal), [ILandAnimal, IAnimal])
        self.assertEqual(get_type_interfaces(Cat), [IAnimal])
        self.assertEqual(get_type_interfaces(Dog), [ILandAnimal, IAnimal])
        self.assertEqual(get_type_interfaces(Mongrel), [ILandAnimal, IAnimal])
        self.assertEqual(get_type_interfaces(Car), [])
        self.assertEqual(get_type_interfaces(len), [])
        self.assertEqual(get_type_interfaces('hello'), [])
