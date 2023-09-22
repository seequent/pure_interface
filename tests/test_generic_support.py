import unittest
import pure_interface
from typing import TypeVar, List, Iterable

T = TypeVar('T')


class IMyInterface(pure_interface.Interface, Iterable[str]):
    def foo(self) -> str:
        pass


class IMyGenericInterface(pure_interface.Interface, Iterable[T]):
    def foo(self) -> T:
        pass


class Impl(List[str], IMyInterface):
    def foo(self):
        return 'foo'


class StrImpl(List[str], IMyGenericInterface[str]):
    def foo(self):
        return 'foo'


class GenericImpl(List[T], IMyGenericInterface[T]):
    def foo(self):
        return T('foo')


class TestGenericSupport(unittest.TestCase):

    def test_generics_are_interfaces(self):
        self.assertTrue(pure_interface.type_is_interface(IMyInterface))
        self.assertTrue(pure_interface.type_is_interface(IMyGenericInterface))

    def test_can_use_iterable(self):
        imp = Impl()
        imp.append('hello')
        imp = StrImpl()
        imp.append('hello')
        imp = GenericImpl[int]()
        imp.append(34)

