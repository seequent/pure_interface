from dataclasses import dataclass
import unittest

from pure_interface import *


class IFoo(Interface):
    a: int
    b: str

    def foo(self):
        pass


@dataclass
class Foo(IFoo):
    c: float = 12.0

    def foo(self):
        return 'a={}, b={}, c={}'.format(self.a, self.b, self.c)


class IBar(IFoo, Interface):
    a: Foo


class TestDataClasses(unittest.TestCase):
    def test_data_class(self):
        try:
            f = Foo(a=1, b='two')
        except Exception as exc:
            self.fail(str(exc))

        self.assertEqual(1, f.a)
        self.assertEqual('two', f.b)
        self.assertEqual(12.0, f.c)

    def test_data_arg_order(self):
        try:
            f = Foo(2, 'two', 34.0)
        except Exception as exc:
            self.fail(str(exc))
        self.assertEqual(2, f.a)
        self.assertEqual('two', f.b)
        self.assertEqual(34.0, f.c)
        self.assertEqual('a=2, b=two, c=34.0', f.foo())

    def test_data_class_with_args(self):
        try:
            @dataclass(frozen=True)
            class FrozenFoo(IFoo):
                def foo(self):
                    return 'a={}, b={}'.format(self.a, self.b)

        except Exception as exc:
            self.fail(str(exc))

        f = Foo(a=1, b='two')
        self.assertEqual(1, f.a)
        self.assertEqual('two', f.b)

    def test_read_only_attr(self):
        @dataclass
        class RoFoo(IFoo):
            c: int

            @property
            def b(self):
                return 'str'

            def foo(self):
                return 'a={}, b={}, c={}'.format(self.a, self.b, self.c)

        f = RoFoo(a=1, c=3)
        self.assertEqual({'a': int, 'c': int}, RoFoo.__annotations__)
        self.assertEqual(1, f.a)
        self.assertEqual('str', f.b)

    def test_attr_present(self):
        @dataclass
        class AFoo(IFoo):
            a = 10

            def foo(self):
                return 'a={}, b={}, c={}'.format(self.a, self.b, self.c)

        f = AFoo(b='str')
        self.assertEqual({'b': str}, AFoo.__annotations__)
        self.assertEqual(10, f.a)
        self.assertEqual('str', f.b)

    def test_annotations_override(self):
        """ ensure overridden annotations are used correctly """
        @dataclass
        class Bar(IBar):

            def foo(self):
                return 'a={}, b={}'.format(self.a, self.b)

        self.assertEqual({'a': int, 'b': str}, IFoo.__annotations__)
        self.assertEqual({'a': Foo, 'b': str}, IBar.__annotations__)
        self.assertEqual({'a': Foo, 'b': str}, Bar.__annotations__)
        b = Bar(a=Foo(a=1, b='two'), b='three')
        self.assertIsInstance(b.a, Foo)

    def test_non_direct_subclass(self):
        """ ensure no extra annotations are added to the class"""
        class Baz(Foo):
            e: str

        self.assertEqual({'e': str}, Baz.__annotations__)
