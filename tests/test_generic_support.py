import unittest
import pure_interface
import collections.abc
from typing import TypeVar, List, Iterable

T = TypeVar('T')

class MyInterface(pure_interface.Interface, Iterable[str]):
    def foo(self) -> T:
        pass

class MyGenericInterface(pure_interface.Interface, Iterable[T]):
    def foo(self) -> T:
        pass

class Impl(List[str], MyInterface):
    def foo(self):
        return 'foo'

class StrImpl(List[str], MyGenericInterface[str]):
    def foo(self):
        return 'foo'


class GenericImpl(List[T], MyGenericInterface[T]):
    def foo(self):
        return T('foo')


class TestGenericSupport(unittest.TestCase):
    def test_can_use_iterable(self):
        imp = Impl()
        imp.append('hello')
        imp = StrImpl()
        imp.append('hello')
        imp = GenericImpl[int]()
        imp.append(34)

