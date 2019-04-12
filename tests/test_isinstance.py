# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

import pure_interface

try:
    from unittest import mock
except ImportError:
    import mock


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
        self.assertTrue(IAnimal.provided_by(a, allow_implicit=False))

    def test_duck_type_fallback_passes(self):
        class Animal2(object):
            def speak(self, volume):
                print('hello')

            @property
            def height(self):
                return 5

        a = Animal2()
        self.assertFalse(isinstance(a, IAnimal))
        self.assertFalse(IAnimal.provided_by(a, allow_implicit=False))
        self.assertTrue(IAnimal.provided_by(a, allow_implicit=True))
        self.assertIn(Animal2, IAnimal._pi.structural_subclasses)

    def test_duck_type_fallback_can_fail(self):
        class Animal2(object):
            def speak(self, volume):
                print('hello')

        a = Animal2()
        self.assertFalse(isinstance(a, IAnimal))
        self.assertFalse(IAnimal.provided_by(a, allow_implicit=True))

    def test_concrete_subclass_check(self):
        class Cat(object, IAnimal):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

            def happy(self):
                return True

        c = Cat()
        with self.assertRaises(pure_interface.InterfaceError):
            Cat.provided_by(c, allow_implicit=False)

    def test_warning_issued_once(self):
        pure_interface.is_development = True

        class Cat2(object):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            IAnimal.provided_by(Cat2(), allow_implicit=True)
            IAnimal.provided_by(Cat2(), allow_implicit=True)

        self.assertEqual(warn.call_count, 1)
        msg = warn.call_args[0][0]
        self.assertIn('Cat2', msg)
        self.assertIn('IAnimal', msg)

    def test_warning_not_issued(self):
        pure_interface.is_development = False

        class Cat3(object):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            IAnimal.provided_by(Cat3(), allow_implicit=True)

        warn.assert_not_called()
