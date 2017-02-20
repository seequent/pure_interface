# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pure_interface

import unittest


class IAnimal(pure_interface.PureInterface):
    def speak(self, volume):
        pass

    @pure_interface.abstractproperty
    def height(self):
        return None


class TestIsInstanceChecks(unittest.TestCase):
    def test_abc_register(self):
        class Animal(object):
            pass

        IAnimal.register(Animal)
        a = Animal()
        self.assertTrue(isinstance(a, IAnimal))

    def test_duck_type_fallback_passes(self):
        class Animal2(object):
            def speak(self, volume):
                print('hello')

            def __init__(self):
                self.height = 43

        a = Animal2()
        self.assertTrue(isinstance(a, IAnimal))

    def test_duck_type_fallback_fails(self):
        class Animal2(object):
            def speak(self, volume):
                print('hello')

        a = Animal2()
        self.assertFalse(isinstance(a, IAnimal))

    def test_isinstance_duck_type_check_registers(self):
        class Animal2(object):
            def speak(self, volume):
                print('hello')

            @property
            def height(self):
                return 43

        a = Animal2()
        self.assertNotIn(Animal2, IAnimal._abc_registry)
        self.assertTrue(isinstance(a, IAnimal))
        self.assertIn(Animal2, IAnimal._abc_registry)

    def test_issubclass_duck_type_check_registers(self):
        class Animal3(object):
            def speak(self, volume):
                print('hello')

            @property
            def height(self):
                return 43

        self.assertNotIn(Animal3, IAnimal._abc_registry)
        self.assertTrue(issubclass(Animal3, IAnimal))
        self.assertIn(Animal3, IAnimal._abc_registry)

    def test_concrete_subclass_check(self):
        class Cat(object, IAnimal):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

            def happy(self):
                return True

        class StripeyCat(object):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

        sc = StripeyCat()
        self.assertFalse(isinstance(sc, Cat))
