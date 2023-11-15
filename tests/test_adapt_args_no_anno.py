import unittest

import pure_interface.errors

try:
    from unittest import mock
except ImportError:
    import mock

from pure_interface import adapt_args, Interface
import pure_interface


class I1(Interface):
    foo = None

    def bar(self):
        pass


class I2(Interface):
    bar = None

    def foo(self):
        pass


class Thing1(I1):
    def __init__(self):
        self.foo = 'foo'

    def bar(self):
        print('bar:', self.foo)


class Thing2(I2):
    def __init__(self):
        self.bar = 'bar'

    def foo(self):
        print('foo:', self.bar)


@adapt_args(y=I1)
def some_func(x, y):
    pass


@adapt_args(b=I2)
def other_func(a, b=None):
    pass


class TestAdaptArgsNoAnno(unittest.TestCase):
    def test_adapt_args_works(self):
        thing1 = Thing1()
        adapt = mock.MagicMock()
        with mock.patch('pure_interface.InterfaceType.optional_adapt', new=adapt):
            some_func(3, thing1)

        self.assertEqual(1, adapt.call_count)
        adapt.assert_called_once_with(I1, thing1)

    def test_adapt_optional_args_works_with_none(self):
        thing1 = Thing1()
        adapt = mock.MagicMock()
        with mock.patch('pure_interface.InterfaceType.optional_adapt', new=adapt):
            other_func(thing1)

        adapt.assert_called_once_with(I2, None)

    def test_adapt_optional_args_works(self):
        thing1 = Thing1()
        thing2 = Thing2()
        adapt = mock.MagicMock()
        with mock.patch('pure_interface.InterfaceType.optional_adapt', new=adapt):
            other_func(thing1, thing2)

        adapt.assert_called_once_with(I2, thing2)

    def test_no_annotations_warning(self):
        with mock.patch('warnings.warn') as warn:
            @adapt_args
            def no_anno(x, y):
                pass

            self.assertEqual(1, warn.call_count)

    def test_error_raised_if_arg_not_subclass(self):
        with self.assertRaises(pure_interface.errors.AdaptionError):
            @adapt_args(x=int)
            def some_func(x):
                pass

    def test_type_error_raised_if_positional_arg_not_func(self):
        with self.assertRaises(pure_interface.errors.AdaptionError):
            @adapt_args(I2)
            def some_func(x):
                pass

    def test_type_error_raised_if_multiple_positional_args(self):
        with self.assertRaises(pure_interface.errors.AdaptionError):
            @adapt_args(I1, I2)
            def some_func(x):
                pass

    def test_type_error_raised_if_mixed_args(self):
        with self.assertRaises(pure_interface.errors.AdaptionError):
            @adapt_args(I1, y=I2)
            def some_func(x, y):
                pass

    def test_wrong_args_type_raises(self):
        thing2 = Thing2()
        with self.assertRaises(ValueError):
            some_func(3, thing2)
