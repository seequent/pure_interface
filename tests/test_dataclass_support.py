import unittest
from pure_interface import *


class IFoo(Interface):
    a: int
    b: str

    def foo(self):
        pass


if 'dataclass' in globals():
    @dataclass
    class Foo(IFoo, object):
        c: float = 12.0

        def foo(self):
            return 'a={}, b={}, c={}'.format(self.a, self.b, self.c)


    class TestDataClasses(unittest.TestCase):
        def test_data_class(self):
            try:
                f = Foo(a=1, b='two')
                self.assertEqual(1, f.a)
                self.assertEqual('two', f.b)
                self.assertEqual(12.0, f.c)
            except Exception as exc:
                self.fail(str(exc))

        def test_data_arg_order(self):
            try:
                f = Foo(2, 'two', 34.0)
                self.assertEqual(2, f.a)
                self.assertEqual('two', f.b)
                self.assertEqual(34.0, f.c)
                self.assertEqual('a=2, b=two, c=34.0', f.foo())
            except Exception as exc:
                self.fail(str(exc))

        def test_data_class_with_args(self):
            try:
                @dataclass(frozen=True)
                class FrozenFoo(IFoo, object):
                    c: float = 12.0

                    def foo(self):
                        return 'a={}, b={}, c={}'.format(self.a, self.b, self.c)

            except Exception as exc:
                self.fail(str(exc))

            f = Foo(a=1, b='two')
            self.assertEqual(1, f.a)
            self.assertEqual('two', f.b)
            self.assertEqual(12.0, f.c)
