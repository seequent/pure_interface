# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import mock
import unittest

import pure_interface


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

    def test_warning_issued_once(self):
        pure_interface.WARN_ABOUT_UNNCESSARY_DUCK_TYPING = True

        class Cat2(object):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            issubclass(Cat2, IAnimal)
            issubclass(Cat2, IAnimal)

        self.assertEqual(warn.call_count, 1)
        msg = warn.call_args[0][0]
        self.assertIn('Cat2', msg)
        self.assertIn('IAnimal', msg)

    def test_warning_not_issued(self):
        pure_interface.WARN_ABOUT_UNNCESSARY_DUCK_TYPING = False

        class Cat3(object):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            issubclass(Cat3, IAnimal)

        warn.assert_not_called()
