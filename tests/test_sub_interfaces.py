import dataclasses
import unittest

import pure_interface


class ILarger(pure_interface.Interface):
    a: int
    b: int
    c: int

    def e(self):
        pass

    def f(self, arg1, arg2, *kwargs):
        pass

    def g(self, /, a, *, b):
        pass


@pure_interface.sub_interface_of(ILarger)
class ISmaller(pure_interface.Interface):
    b: int

    def e(self):
        pass


@pure_interface.adapts(int, ILarger)
def larger_int(i):
    return Larger(i, i, i)


@dataclasses.dataclass
class Larger(ILarger):

    def e(self):
        return 'e'

    def f(self, arg1, arg2, *kwargs):
        return arg1, arg2, kwargs

    def g(self, /, a, *, b):
        return a, b


class TestAdaption(unittest.TestCase):
    def test_large_registered(self):
        big = Larger(1, 2, 3)
        self.assertTrue(isinstance(big, ISmaller))

    def test_large_adapts(self):
        # sanity check
        big = ILarger.adapt(5)
        self.assertEqual(big.b, 5)
        # assert
        try:
            s = ISmaller.adapt(4)
        except pure_interface.InterfaceError:
            self.fail('ISmaller does not adapt ILarger')

        self.assertEqual(s.b, 4)

    def test_fails_when_empty(self):
        with self.assertRaisesRegex(pure_interface.InterfaceError, 'Sub-interface IEmpty is empty'):
            @pure_interface.sub_interface_of(ILarger)
            class IEmpty(pure_interface.Interface):
                pass

    def test_fails_when_arg_not_interface(self):
        with self.assertRaisesRegex(pure_interface.InterfaceError,
                                    "sub_interface_of argument <class 'int'> is not an interface type"):
            @pure_interface.sub_interface_of(int)
            class ISubInterface(pure_interface.Interface):
                def __sub__(self, other):
                    pass

    def test_fails_when_class_not_interface(self):
        with self.assertRaisesRegex(pure_interface.InterfaceError,
                                    'class decorated by sub_interface_of must be an interface type'):
            @pure_interface.sub_interface_of(ILarger)
            class NotInterface:
                pass

    def test_fails_when_attr_mismatch(self):
        with self.assertRaisesRegex(pure_interface.InterfaceError,
                                    'NotSmaller has attributes that are not on ILarger: z'):
            @pure_interface.sub_interface_of(ILarger)
            class INotSmaller(pure_interface.Interface):
                z: int

    def test_fails_when_methods_mismatch(self):
        with self.assertRaisesRegex(pure_interface.InterfaceError,
                                    'NotSmaller has methods that are not on ILarger: x'):
            @pure_interface.sub_interface_of(ILarger)
            class INotSmaller(pure_interface.Interface):
                def x(self):
                    pass

    def test_fails_when_signatures_mismatch(self):
        with self.assertRaisesRegex(pure_interface.InterfaceError,
                                    'Signature of method f on ILarger and INotSmaller must match exactly'):
            @pure_interface.sub_interface_of(ILarger)
            class INotSmaller(pure_interface.Interface):
                def f(self, arg1, arg2, foo=3):
                    pass
