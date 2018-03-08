# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pure_interface

import unittest
import inspect
import types


class IAnimal(pure_interface.PureInterface):
    def speak(self, volume):
        pass


class IPlant(pure_interface.PureInterface):
    def grow(self, height=10):
        pass


class ADescriptor(object):
    def __get__(self, instance, owner):
        return None


def func1(a, b, c):
    pass


def func2(a, b, c=None):
    pass


def func3(a=None, b=None):
    pass


def func4():
    pass


def test_call(func, arg_spec):
    # type: (types.FunctionType, inspect.ArgSpec) -> bool
    if arg_spec.defaults:
        n_defaults = len(arg_spec.defaults)
        kwargs = {a: a for a in arg_spec.args[-n_defaults:]}
        args = arg_spec.args[:-n_defaults]
    else:
        args = arg_spec.args
        kwargs = {}
    try:
        func(*args, **kwargs)
    except TypeError:
        return False
    try:
        func(*args)
    except TypeError:
        return False
    return True


class TestFunctionSignatureChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.IS_DEVELOPMENT = True

    def check_signatures(self, int_func, impl_func, expected_result):
        interface_sig = pure_interface.getargspec(int_func)
        concrete_sig = pure_interface.getargspec(impl_func)
        reality = test_call(impl_func, interface_sig)
        self.assertEqual(expected_result, reality, 'Reality does not match expectations')
        result = pure_interface._signatures_are_consistent(concrete_sig, interface_sig)
        self.assertEqual(expected_result, result, 'Signature test gave wrong answer')

    def test_tests(self):
        self.check_signatures(func1, func1, True)
        self.check_signatures(func2, func2, True)

        self.check_signatures(func2, func1, False)
        self.check_signatures(func1, func2, True)

        self.check_signatures(func2, func3, False)
        self.check_signatures(func3, func2, False)

        self.check_signatures(func3, func4, False)
        self.check_signatures(func4, func3, True)

    def test_varargs(self):
        def varargs(*args):
            pass

        self.check_signatures(func1, varargs, True)
        self.check_signatures(func2, varargs, False)
        self.check_signatures(func3, varargs, False)
        self.check_signatures(func4, varargs, True)

    def test_pos_varargs(self):
        def pos_varargs(a, *args):
            pass

        self.check_signatures(func1, pos_varargs, True)
        self.check_signatures(func2, pos_varargs, False)
        self.check_signatures(func3, pos_varargs, False)
        self.check_signatures(func4, pos_varargs, False)

    def test_keywords(self):
        def keywords(**kwargs):
            pass

        self.check_signatures(func1, keywords, False)
        self.check_signatures(func2, keywords, False)
        self.check_signatures(func3, keywords, True)
        self.check_signatures(func4, keywords, True)

    def test_def_keywords(self):
        def kwarg_keywords(c=4, **kwargs):
            pass

        def kwarg_keywords2(a=4, **kwargs):
            pass

        self.check_signatures(func1, kwarg_keywords, False)
        self.check_signatures(func2, kwarg_keywords, False)
        self.check_signatures(func3, kwarg_keywords, True)
        self.check_signatures(func3, kwarg_keywords, True)
        self.check_signatures(func4, kwarg_keywords, True)

    def test_vararg_keywords(self):
        def vararg_keywords(*args, **kwargs):
            pass

        self.check_signatures(func1, vararg_keywords, True)
        self.check_signatures(func2, vararg_keywords, True)
        self.check_signatures(func3, vararg_keywords, True)
        self.check_signatures(func4, vararg_keywords, True)

    def test_pos_kwarg_vararg(self):
        def pos_kwarg_vararg(a, c=4, *args):
            pass

        self.check_signatures(func1, pos_kwarg_vararg, True)
        self.check_signatures(func2, pos_kwarg_vararg, False)
        self.check_signatures(func3, pos_kwarg_vararg, False)
        self.check_signatures(func4, pos_kwarg_vararg, False)

    def test_all(self):
        def all(a, c=4, *args, **kwargs):
            pass

        self.check_signatures(func1, all, True)
        self.check_signatures(func2, all, False)
        self.check_signatures(func3, all, False)
        self.check_signatures(func4, all, False)

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

    def test_all_functions_checked(self):  # issue #7
        class IWalkingAnimal(IAnimal):
            def walk(self, distance):
                pass

        with self.assertRaises(pure_interface.InterfaceError):
            class Animal(object, IWalkingAnimal):
                speak = ADescriptor()

                def walk(self, volume):
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
