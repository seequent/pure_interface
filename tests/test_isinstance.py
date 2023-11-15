import io
import unittest
from unittest import mock
import warnings

import pure_interface
from tests.interface_module import IAnimal


class TestIsInstanceChecks(unittest.TestCase):
    def test_abc_register(self):
        class Animal(object):
            pass

        IAnimal.register(Animal)
        a = Animal()
        self.assertTrue(isinstance(a, IAnimal))
        self.assertTrue(IAnimal.provided_by(a))

    def test_duck_type_fallback_passes(self):
        class Animal2(object):
            def speak(self, volume):
                print('hello')

            @property
            def height(self):
                return 5

        a = Animal2()
        self.assertFalse(isinstance(a, IAnimal))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.assertTrue(IAnimal.provided_by(a))
        self.assertIn(Animal2, IAnimal._pi.structural_subclasses)

    def test_duck_type_fallback_can_fail(self):
        class Animal2(object):
            def speak(self, volume):
                print('hello')

        a = Animal2()
        self.assertFalse(isinstance(a, IAnimal))
        self.assertFalse(IAnimal.provided_by(a))

    def test_concrete_subclass_check(self):
        class Cat(IAnimal):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

            def happy(self):
                return True

        c = Cat()
        with self.assertRaises(pure_interface.InterfaceError):
            Cat.provided_by(c)

    def test_warning_issued_once(self):
        pure_interface.set_is_development(True)

        class Cat2(object):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            IAnimal.provided_by(Cat2())
            IAnimal.provided_by(Cat2())

        self.assertEqual(warn.call_count, 1)

    def test_warning_not_issued(self):
        pure_interface.set_is_development(False)

        class Cat3(object):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            IAnimal.provided_by(Cat3())

        warn.assert_not_called()

    def test_warning_contents(self):
        pure_interface.set_is_development(True)

        class Cat4(object):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

        s = io.StringIO()
        with mock.patch('sys.stderr', new=s):
            IAnimal.provided_by(Cat4())

        msg = s.getvalue()
        self.assertIn('Cat4', msg)
        self.assertIn(Cat4.__module__, msg)
        self.assertNotIn('pure_interface', msg.split('\n')[0])
        self.assertIn('IAnimal', msg)

    def test_warning_contents_adapt(self):
        pure_interface.set_is_development(True)

        class Cat5(object):
            def speak(self, volume):
                print('meow')

            @property
            def height(self):
                return 35

        s = io.StringIO()
        with mock.patch('sys.stderr', new=s):
            IAnimal.adapt(Cat5(), allow_implicit=True)

        msg = s.getvalue()
        self.assertIn('Cat5', msg)
        self.assertIn(Cat5.__module__, msg)
        self.assertNotIn('pure_interface', msg.split('\n')[0])
        self.assertIn('IAnimal', msg)

