import dataclasses

import pure_interface
import unittest
from unittest import mock

from pure_interface import delegation, Interface


class ITalker(Interface):
    def talk(self):
        pass


class ISubTalker(ITalker, Interface):
    def chat(self):
        pass


class ISpeaker(Interface):
    def speak(self, volume):
        pass


class Speaker(ISpeaker):
    def speak(self, volume):
        return 'speak'


class Talker(ITalker):
    def talk(self):
        return 'talk'

    def chat(self):
        return 'chat'


class IPoint(Interface):
    x: int
    y: int

    def to_str(self) -> str:
        pass


class IPoint3(IPoint, Interface):
    z: int


@dataclasses.dataclass
class PointImpl:
    x: int
    y: int
    z: int


class Point(IPoint):
    def __init__(self, x=0, y=1):
        self.x = int(x)
        self.y = int(y)

    def to_str(self) -> str:
        return f'{self.x}, {self.y}'


class DFallback(delegation.Delegate, ITalker):
    pi_attr_fallback = 'impl'

    def __init__(self, impl):
        self.impl = impl


class DSubFallback(DFallback, ISubTalker):
    pass


class DSubFallback2(DFallback, ISubTalker):
    pi_attr_fallback = 'impl'


class DAttrMap(delegation.Delegate, IPoint):
    pi_attr_mapping = {'x': 'a.x',
                       'y': 'b.y',
                       'to_str': 'b.to_str',
                       }

    def __init__(self, a, b):
        self.a = a
        self.b = b


class DDelegateList(delegation.Delegate, IPoint):
    pi_attr_delegates = {'a': ['x', 'to_str'],
                         'b': ['x', 'y']}

    def __init__(self, a, b):
        self.a = a
        self.b = b


class DDelegateIFace(delegation.Delegate, IPoint, ITalker):
    pi_attr_delegates = {'a': IPoint,
                         'b': ITalker}

    def __init__(self, a, b):
        self.a = a
        self.b = b


class DelegateOverride(delegation.Delegate, ITalker):
    pi_attr_delegates = {'a': ITalker}

    def __init__(self, a):
        self.a = a

    def talk(self):
        return 'hello'


class DelegateAttrOverride(delegation.Delegate, IPoint):
    pi_attr_fallback = 'a'

    def __init__(self, a):
        self.a = a
        self._x = 'x'

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        self._x = x


class DoubleDottedDelegate(delegation.Delegate):
    x: int
    y: int

    pi_attr_mapping = {'x': 'a.b.x',
                       'y': 'a.b.y'}

    def __init__(self):
        a = Talker()
        a.b = Point(3, 4)
        self.a = a


class ScaledPoint(pure_interface.Delegate, IPoint):
    pi_attr_fallback = '_p'

    def __init__(self, point):
        self._p = point

    @property
    def y(self):
        return self._p.y * 2

    @y.setter
    def y(self, value):
        self._p.y = int(value // 2)

    def to_str(self) -> str:
        return f'{self.x}, {self.y}'


class ScaledPoint3(ScaledPoint, IPoint3):
    pi_attr_fallback = '_p'


class DelegateTest(unittest.TestCase):
    def test_descriptor_get_class(self):
        d = pure_interface.delegation._Delegated('foo.bar')

        e = d.__get__(None, mock.Mock)
        self.assertIs(d, e)

    def test_descriptor_get(self):
        m = mock.Mock()
        d = pure_interface.delegation._Delegated('foo.bar.baz')

        v = d.__get__(m, type(m))

        self.assertIs(v, m.foo.bar.baz)

    def test_descriptor_set(self):
        m = mock.Mock()
        v = mock.Mock()
        d = pure_interface.delegation._Delegated('foo.bar.baz')

        d.__set__(m, v)
        w = d.__get__(m, type(m))

        self.assertIs(v, m.foo.bar.baz)
        self.assertIs(v, w)

    def test_fallback(self):
        d = DFallback(Talker())

        self.assertEqual('talk', d.talk())
        with self.assertRaises(AttributeError):
            d.x

    def test_attr_map(self):
        a = Point(1, 2)
        b = Point(3, 4)

        d = DAttrMap(a, b)

        self.assertEqual(1.0, d.x)
        self.assertEqual(4.0, d.y)

        with self.assertRaises(AttributeError):
            d.z

    def test_delegate_list(self):
        a = Point(1, 2)
        b = Point(3, 4)

        d = DDelegateList(a, b)

        self.assertEqual(1, d.x)
        self.assertEqual(4, d.y)

    def test_delegate_iface(self):
        a = Point(1, 2)
        b = Talker()

        d = DDelegateIFace(a, b)

        self.assertEqual(1, d.x)
        self.assertEqual(2, d.y)
        self.assertEqual('talk', d.talk())

    def test_attr_set(self):
        a = Point(1, 2)
        b = Point(3, 4)

        d = DAttrMap(a, b)
        d.x = 5
        d.y = 7

        self.assertEqual(5, a.x)
        self.assertEqual(5, d.x)
        self.assertEqual(7, b.y)
        self.assertEqual(7, d.y)

    def test_check_duplicate(self):
        with self.assertRaises(ValueError):
            class BadDelegate(delegation.Delegate):
                pi_attr_mapping = {'x': 'a.x'}
                pi_attr_delegates = {'x': ['foo', 'bar']}

    def test_check_delegate_in_attr_map(self):
        with self.assertRaises(ValueError):
            class BadDelegate(delegation.Delegate):
                pi_attr_mapping = {'foo': 'a.x'}
                pi_attr_delegates = {'x': ['foo', 'bar']}

    def test_delegate_method_override(self):
        t = Talker()
        d = DelegateOverride(t)
        self.assertEqual('hello', d.talk())

    def test_delegate_override(self):
        t = Talker()
        d = DelegateOverride(t)
        self.assertEqual('hello', d.talk())

    def test_delegate_attr_override(self):
        p = Point()
        d = DelegateAttrOverride(p)
        self.assertEqual('x', d.x)
        d.x = 'y'
        self.assertEqual(0, p.x)

    def test_double_dotted_delegate(self):
        d = DoubleDottedDelegate()
        self.assertEqual(3, d.x)
        self.assertEqual(4, d.y)
        d.x = 1
        self.assertEqual(1, d.a.b.x)

    def test_delegate_subclass(self):
        """test that subclass methods are not delegated """
        p = PointImpl(1, 2, 3)
        d3 = ScaledPoint3(p)
        self.assertEqual(4, d3.y)
        self.assertEqual('1, 4', d3.to_str())
        d3.y = 8  # delegates to p
        self.assertEqual(4, p.y)
        self.assertEqual(3, d3.z)

    def test_delegate_subclass_fallback(self):
        """Check fallback delegates are not used for subclass interface attributes too."""
        with self.assertRaises(TypeError):
            DSubFallback(Talker())  # no implementation of chat

    def test_delegate_subclass_fallback2(self):
        """Check subclass fallbacks are used for missing attributes."""
        d = DSubFallback2(Talker())
        self.assertEqual('chat', d.chat())

    def test_delegate_provides_fails(self):
        with self.assertRaises(pure_interface.InterfaceError):
            DFallback.provided_by(ITalker)


class CompositionTest(unittest.TestCase):

    def test_type_composition(self):
        a = Point(1, 2)
        b = Talker()

        T = delegation.composed_type(IPoint, ITalker)
        S = delegation.composed_type(IPoint, ITalker)
        t = T(a, b)

        self.assertIs(S, T)
        self.assertTrue(issubclass(T, IPoint))
        self.assertTrue(issubclass(T, ITalker))
        self.assertTrue(issubclass(T, delegation.Delegate))
        self.assertEqual(1, t.x)
        self.assertEqual(2, t.y)
        self.assertEqual('talk', t.talk())

    def test_type_composition_checks(self):
        with self.assertRaises(ValueError):
            delegation.composed_type(IPoint)

        with self.assertRaises(ValueError):
            delegation.composed_type('hello')

        with self.assertRaises(ValueError):
            delegation.composed_type(Talker)

    def test_type_composition_init_checks(self):
        a = Point(1, 2)
        b = Talker()
        T = delegation.composed_type(IPoint, ITalker)

        with self.assertRaises(ValueError):
            T(b, a)

    def test_type_composition_commutative(self):
        a = Point(1, 2)
        b = Talker()
        S = delegation.composed_type(ITalker, IPoint)
        T = delegation.composed_type(IPoint, ITalker)

        s = S(b, a)
        t = T(a, b)
        self.assertTrue(T.provided_by(s))
        self.assertTrue(S.provided_by(t))

    def test_type_composition_chain(self):
        a = Point(1, 2)
        b = Talker()
        c = Speaker()

        S = delegation.composed_type(ITalker, IPoint)
        T = delegation.composed_type(IPoint, ITalker, ISpeaker)

        t = T(a, b, c)
        s = S(b, a)
        self.assertTrue(S.provided_by(t))
        self.assertTrue(T.provided_by(t))
        self.assertTrue(S.provided_by(s))
        self.assertFalse(T.provided_by(s))

    def test_unused_fallback_is_benign(self):
        try:
            class UnusedFallbackDelegate(delegation.Delegate):
                pi_attr_fallback = 'a'

                def __init__(self):
                    self.a = Talker()

            x = UnusedFallbackDelegate()

        except Exception as exc:
            self.fail(str(exc))

    def test_fail_on_unsupported_type(self):
        with self.assertRaises(ValueError):
            delegation.composed_type(str, int)

    def test_too_many_interfaces(self):
        with mock.patch('pure_interface.delegation._letters', 'a'):
            with self.assertRaises(ValueError):
                delegation.composed_type(ITalker, IPoint)
