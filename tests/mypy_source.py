"""With the pure-interface mypy plugin enabled, mypy should validate this file without error.

This is working except for dataclasses __init__ call arguments.
"""

import abc
import dataclasses

import pure_interface


class BaseInterface(pure_interface.Interface):
    def speak(self, volume) -> str:
        pass

    @classmethod
    def a_class_method(cls) -> list:
        pass


class MyInterface(BaseInterface, pure_interface.Interface):
    foo: int

    @abc.abstractmethod
    def weight(self, arg: int) -> str:
        """weight of the thing."""

    @property
    def height(self) -> float:
        pass

    @staticmethod
    def a_static_method() -> int:
        pass


class MyThing(MyInterface):
    def __init__(self):
        self.foo = 3
        self._height = 34.3

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, height):
        self._height = height

    def weight(self, arg: int) -> str:
        if arg > 0:
            return "3" * arg
        else:
            return ""

    def speak(self, volume) -> str:
        return "hello"

    @classmethod
    def a_class_method(cls):
        return []

    @staticmethod
    def a_static_method() -> int:
        return 6


@dataclasses.dataclass
class DC(MyInterface):
    def weight(self, arg: int) -> str:
        return f"{arg}"

    def speak(self, volume) -> str:
        return "hello"

    @classmethod
    def a_class_method(cls):
        return []

    @staticmethod
    def a_static_method() -> int:
        return 6


class FBDelegate(pure_interface.Delegate, MyInterface):
    pi_attr_fallback = "_a"

    def __init__(self, impl) -> None:
        self._a = impl


class AttrListDelegate(pure_interface.Delegate):
    pi_attr_delegates = {"a": ["height", "weight"], "b": ["speak"]}

    def __init__(self, impl) -> None:
        self.a = impl
        self.b = impl


class AttrTypeDelegate(pure_interface.Delegate):
    pi_attr_delegates = {"a": BaseInterface}

    def __init__(self, impl) -> None:
        self.a = impl


class MappingDelegate(pure_interface.Delegate):
    pi_attr_mapping = {"wibble": "a.speak", "bar": "a.foo"}

    def __init__(self, impl) -> None:
        self.a = impl


t = MyThing()
fbd = FBDelegate(t)
if fbd.weight(3) == "3":
    print("all good")
w = fbd.foo * 2
fbd.height = 34.8

ald = AttrListDelegate(t)
a = ald.height
b = ald.weight(4)
c = ald.speak(4)

atd = AttrTypeDelegate(t)
x = atd.speak(6)

md = MappingDelegate(t)
y = md.wibble(2)
z = md.bar

# these 2 lines still raise call-arg errors.
dc1 = DC(4, 3.7)
dc2 = DC(foo=4, height=3.7)

dc1.speak(dc1.foo)
dc2.height = 23.7
