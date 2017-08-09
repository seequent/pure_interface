# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pure_interface

import unittest


class IAnimal(pure_interface.PureInterface):
    def speak(self, volume):
        pass


class IPlant(pure_interface.PureInterface):
    def grow(self, height=10):
        pass


class TestFunctionSignatureChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.IS_DEVELOPMENT = True

    def test_diff_names_fails(self):
        # concrete subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Animal(object, IAnimal):
                def speak(self, loudness):
                    pass

        # abstract subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Animal2(IAnimal):
                def speak(self, loudness):
                    pass

    def test_too_few_fails(self):
        # concrete subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Animal(object, IAnimal):
                def speak(self):
                    pass

        # abstract subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Animal2(IAnimal):
                def speak(self):
                    pass

    def test_too_many_fails(self):
        # concrete subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Animal(object, IAnimal):
                def speak(self, volume, msg):
                    pass

        # abstract subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Animal2(IAnimal):
                def speak(self, volume, msg):
                    pass

    def test_new_with_default_passes(self):
        class Animal(object, IAnimal):
            def speak(self, volume, msg='hello'):
                return '{} ({})'.format(msg, volume)

        # abstract subclass
        class IAnimal2(IAnimal):
            def speak(self, volume, msg='hello'):
                pass

        class Animal3(object, IAnimal2):
            def speak(self, volume, msg='hello'):
                return '{} ({})'.format(msg, volume)

        a = Animal()
        b = Animal3()
        self.assertEqual(a.speak('loud'), 'hello (loud)')
        self.assertEqual(b.speak('loud'), 'hello (loud)')

    def test_adding_default_passes(self):
        class Animal(object, IAnimal):
            def speak(self, volume='loud'):
                return 'hello ({})'.format(volume)

        a = Animal()
        self.assertEqual(a.speak(), 'hello (loud)')

    def test_increasing_required_params_fails(self):
        # concrete subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Plant(object, IPlant):
                def grow(self, height):
                    return height + 5

        # abstract subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Plant2(IPlant):
                def grow(self, height):
                    pass


class TestDisableFunctionSignatureChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.IS_DEVELOPMENT = False

    def test_too_many_passes(self):
        try:
            class Animal(object, IAnimal):
                def speak(self, volume, msg):
                    pass
            a = Animal()
        except pure_interface.InterfaceError as exc:
            self.fail('Unexpected error {}'.format(exc))
