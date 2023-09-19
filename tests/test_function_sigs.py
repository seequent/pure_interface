from pure_interface import Interface
import pure_interface

import unittest
import types

from pure_interface import interface


class IAnimal(Interface):
    def speak(self, volume):
        pass


class IPlant(Interface):
    def grow(self, height=10):
        pass


class ADescriptor(object):
    def __get__(self, instance, owner):
        return None


def func1(a, b, c):
    pass


def func2(a, b, c='c'):
    pass


def func3(a='a', b='b'):
    pass


def func4():
    pass


def func5(a, *args):
    pass


def func6(a, **kwargs):
    pass


def func7(a, b='b', *args):
    pass


def func8(*args):
    pass


def func9(**kwargs):
    pass


def func10(*args, **kwargs):
    pass


def func11(a='a', **kwargs):
    pass


def _test_call(spec_func, impl_func, impl_sig, args, kwargs):
    spec_func(*args, **kwargs)
    try:
        impl_func(*args, **kwargs)
    except TypeError:
        return False
    try:
        ba = impl_sig.bind(*args, **kwargs)
    except TypeError:
        return False
    if not all(k == v for k, v in ba.arguments.items() if k not in ('args', 'kwargs')):
        return False
    kwargs = ba.arguments.get('kwargs', {})
    if not all(k == v for k, v in kwargs.items()):
        return False
    return True


def test_call(spec_func: types.FunctionType, impl_func: types.FunctionType) -> bool:
    """ call the function with parameters as indicated by the parameter list
    """
    spec_sig = pure_interface.interface.signature(spec_func)
    impl_sig = pure_interface.interface.signature(impl_func)
    pos_or_kw = [p for p in spec_sig.parameters.values() if p.kind == p.POSITIONAL_OR_KEYWORD]
    pok_args = [p.name for p in pos_or_kw]
    pok_def = {p.name: p.name for p in pos_or_kw if p.default is not p.empty}
    pok_req = [p.name for p in pos_or_kw if p.default is p.empty]
    n_req = len(pok_req)
    # test args can be positional or keyword
    for i in range(len(pos_or_kw)+1):
        args = pok_args[:i]
        kwargs = {x: x for x in pok_args[i:]}
        if not _test_call(spec_func, impl_func, impl_sig, args, kwargs):
            return False
    # test defaults may be omitted
    for i in range(len(pok_def)):
        args = pok_args[:n_req + i]
        if not _test_call(spec_func, impl_func, impl_sig, args, {}):
            return False
        if not _test_call(spec_func, impl_func, impl_sig, (), {x: x for x in args}):
            return False
    # test *args
    if any(p.kind == p.VAR_POSITIONAL for p in spec_sig.parameters.values()):
        if not _test_call(spec_func, impl_func, impl_sig, pok_args + ['more', 'random', 'arguments'], {}):
            return False
    # test **kwargs
    if any(p.kind == p.VAR_KEYWORD for p in spec_sig.parameters.values()):
        extra_kw = {x: x for x in ('more', 'random', 'keywords')}
        if not _test_call(spec_func, impl_func, impl_sig, pok_args, extra_kw):
            return False
        extra_kw.update(pok_def)
        if not _test_call(spec_func, impl_func, impl_sig, pok_req, extra_kw):
            return False
    return True


class TestFunctionSignatureChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.set_is_development(True)

    def check_signatures(self, int_func, impl_func, expected_result):
        interface_sig = pure_interface.interface.signature(int_func)
        concrete_sig = pure_interface.interface.signature(impl_func)
        reality = test_call(int_func, impl_func)
        self.assertEqual(expected_result, reality,
                         '{}, {}. Reality does not match expectations'.format(int_func.__name__, impl_func.__name__))
        result = pure_interface.interface._signatures_are_consistent(concrete_sig, interface_sig)
        self.assertEqual(expected_result, result,
                         '{}, {}. Signature test gave wrong answer'.format(int_func.__name__, impl_func.__name__))

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
        self.check_signatures(func1, func8, False)
        self.check_signatures(func2, func8, False)
        self.check_signatures(func3, func8, False)
        self.check_signatures(func4, func8, True)
        self.check_signatures(func5, func8, False)
        self.check_signatures(func9, func8, False)

    def test_pos_varargs(self):
        self.check_signatures(func1, func5, False)
        self.check_signatures(func2, func5, False)
        self.check_signatures(func3, func5, False)
        self.check_signatures(func4, func5, False)
        self.check_signatures(func6, func5, False)
        self.check_signatures(func7, func5, False)
        self.check_signatures(func8, func5, False)

    def test_keywords(self):
        self.check_signatures(func1, func9, False)
        self.check_signatures(func2, func9, False)
        self.check_signatures(func3, func9, False)
        self.check_signatures(func4, func9, True)
        self.check_signatures(func6, func9, False)
        self.check_signatures(func8, func9, False)

    def test_def_keywords(self):
        def kwarg_keywords(c=4, **kwargs):
            pass

        self.check_signatures(func1, kwarg_keywords, False)
        self.check_signatures(func2, kwarg_keywords, False)
        self.check_signatures(func3, kwarg_keywords, False)
        self.check_signatures(func4, kwarg_keywords, True)
        self.check_signatures(func3, func11, False)
        self.check_signatures(func6, func11, True)

    def test_vararg_keywords(self):
        self.check_signatures(func1, func10, True)
        self.check_signatures(func2, func10, True)
        self.check_signatures(func3, func10, True)
        self.check_signatures(func4, func10, True)
        self.check_signatures(func5, func10, True)
        self.check_signatures(func6, func10, True)
        self.check_signatures(func7, func10, True)
        self.check_signatures(func8, func10, True)
        self.check_signatures(func9, func10, True)
        self.check_signatures(func11, func10, True)

    def test_pos_kwarg_vararg(self):
        def pos_kwarg_vararg(a, c=4, *args):
            pass

        self.check_signatures(func1, pos_kwarg_vararg, False)
        self.check_signatures(func2, pos_kwarg_vararg, False)
        self.check_signatures(func3, pos_kwarg_vararg, False)
        self.check_signatures(func4, pos_kwarg_vararg, False)

    def test_all(self):
        def all(a, b='b', *args, **kwargs):
            pass

        self.check_signatures(func1, all, True)
        self.check_signatures(func2, all, True)
        self.check_signatures(func3, all, False)
        self.check_signatures(func4, all, False)
        self.check_signatures(func6, all, True)
        self.check_signatures(func7, all, True)
        self.check_signatures(func11, all, False)
        self.check_signatures(all, all, True)

    def test_binding_order(self):
        def all(a, c='c', *args, **kwargs):
            pass

        def rev(a, c, b):
            pass
        self.check_signatures(func1, all, False)
        self.check_signatures(func1, rev, False)

    def test_some_more(self):
        self.check_signatures(func1, func5, False)
        self.check_signatures(func2, func7, False)
        self.check_signatures(func5, func5, True)
        self.check_signatures(func5, func8, False)
        self.check_signatures(func5, func11, False)
        self.check_signatures(func6, func11, True)
        self.check_signatures(func7, func11, False)
        self.check_signatures(func8, func5, False)
        self.check_signatures(func9, func11, True)
        self.check_signatures(func11, func9, False)

    def test_diff_names_fails(self):
        # concrete subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Animal(IAnimal):
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
            class Animal(IAnimal):
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
            class Animal(IAnimal):
                def speak(self, volume, msg):
                    pass

    def test_all_functions_checked(self):  # issue #7
        class IWalkingAnimal(IAnimal, Interface):
            def walk(self, distance):
                pass

        with self.assertRaises(pure_interface.InterfaceError):
            class Animal(IWalkingAnimal):
                speak = ADescriptor()

                def walk(self, volume):
                    pass

        # abstract subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Animal2(IAnimal):
                def speak(self, volume, msg):
                    pass

    def test_new_with_default_passes(self):
        class Animal(IAnimal):
            def speak(self, volume, msg='hello'):
                return '{} ({})'.format(msg, volume)

        # abstract subclass
        class IAnimal2(IAnimal):
            def speak(self, volume, msg='hello'):
                pass

        class Animal3(IAnimal2):
            def speak(self, volume, msg='hello'):
                return '{} ({})'.format(msg, volume)

        a = Animal()
        b = Animal3()
        self.assertEqual(a.speak('loud'), 'hello (loud)')
        self.assertEqual(b.speak('loud'), 'hello (loud)')

    def test_adding_default_passes(self):
        class Animal(IAnimal):
            def speak(self, volume='loud'):
                return 'hello ({})'.format(volume)

        a = Animal()
        self.assertEqual(a.speak(), 'hello (loud)')

    def test_increasing_required_params_fails(self):
        # concrete subclass
        with self.assertRaises(pure_interface.InterfaceError):
            class Plant(IPlant):
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
        pure_interface.set_is_development(False)

    def test_too_many_passes(self):
        try:
            class Animal(IAnimal):
                def speak(self, volume, msg):
                    pass
            a = Animal()
        except pure_interface.InterfaceError as exc:
            self.fail('Unexpected error {}'.format(exc))
