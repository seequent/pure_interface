import pure_interface
import unittest
from unittest import mock

from pure_interface import delegation


class ITalker(pure_interface.Interface):
    def talk(self):
        pass


class ISpeaker(pure_interface.Interface):
    def speak(self, volume):
        pass


class Speaker(ISpeaker, object):
    def speak(self, volume):
        return 'speak'


class Talker(ITalker, object):
    def talk(self):
        return 'talk'


class IPoint(pure_interface.Interface):
    x: int
    y: int


class Point(IPoint, object):
    def __init__(self, x=0, y=1):
        self.x = int(x)
        self.y = int(y)


class DFallback(delegation.Delegate, ITalker):
    attr_fallback = 'impl'

    def __init__(self, impl):
        self.impl = impl


class DAttrMap(delegation.Delegate, IPoint):
    attr_mapping = {'x': 'a.x',
                    'y': 'b.y',
                    }

    def __init__(self, a, b):
        self.a = a
        self.b = b


class DDelegateList(delegation.Delegate, IPoint):
    attr_delegates = {'a': ['x'],
                      'b': ['x', 'y']}

    def __init__(self, a, b):
        self.a = a
        self.b = b


class DDelegateIFace(delegation.Delegate, IPoint, ITalker):
    attr_delegates = {'a': IPoint,
                      'b': ITalker}

    def __init__(self, a, b):
        self.a = a
        self.b = b


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
