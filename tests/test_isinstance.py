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

    def test_duck_type_check_registers(self):
        class Animal2(object):
            def speak(self, volume):
                print('hello')

            @property
            def height(self):
                return 43

        a = Animal2()
        self.assertFalse(issubclass(Animal2, IAnimal))
        self.assertTrue(isinstance(a, IAnimal))
        self.assertTrue(issubclass(Animal2, IAnimal))
