import pure_interface
from pure_interface import *

import abc
import unittest

import six

try:
    from unittest import mock
except ImportError:
    import mock

class ADescriptor(object):
    def __init__(self, value):
        self._value = value

    def __get__(self, instance, owner):
        return self._value


class IAnimal(Interface):
    @abstractproperty
    def height(self):
        return None


class IAnimal3(Interface):
    # python 3 style syntax
    @property
    @abstractmethod
    def height(self):
        pass

    @height.setter
    @abstractmethod
    def height(self, height):
        pass


class IGrowingAnimal(Interface):
    def get_height(self):
        return None

    def set_height(self, height):
        pass

    height = abc.abstractproperty(get_height, set_height)


class IPlant(Interface):
    @property
    def height(self):
        return None


class IGrowingPlant(Interface):
    @property
    def height(self):
        return None

    @height.setter
    def height(self, height):
        pass


class IFunkyMethods(Interface):
    @abstractclassmethod
    def acm(cls):
        return None

    @classmethod
    def cm(cls):
        return None

    @abstractstaticmethod
    def asm():
        return None

    @staticmethod
    def sm():
        return None


class ISimple(Interface):
    def foo(self):
        pass


class ICrossImplementation(Interface):
    """ interface to test class attributes implemented as properties and vice versa """
    a = None
    b = None

    @property
    def c(self):
        pass

    @property
    def d(self):
        pass


class TestImplementationChecks(unittest.TestCase):
    def test_instantiation_fails(self):
        with self.assertRaises(InterfaceError):
            Interface()
        with self.assertRaises(InterfaceError) as exc:
            IPlant()
        assert 'Interfaces cannot be instantiated' in str(exc.exception)
        with self.assertRaises(InterfaceError):
            IAnimal()
        with self.assertRaises(InterfaceError):
            IAnimal3()

    def test_concrete_base_detection(self):
        class Concrete(Interface, object):
            pass

        self.assertFalse(Concrete._pi.type_is_pure_interface)
        try:
            c = Concrete()
        except Exception as exc:
            self.fail('Instantiation failed {}'.format(exc))

    def test_concrete_base_detection2(self):
        class B(object):
            def __init__(self):
                self.foo = 'bar'

        class Concrete(B, Interface):
            pass

        self.assertFalse(Concrete._pi.type_is_pure_interface)
        try:
            c = Concrete()
        except Exception as exc:
            self.fail('Instantiation failed {}'.format(exc))

    def test_concrete_abc_detection(self):
        @six.add_metaclass(abc.ABCMeta)
        class B(object):
            def __init__(self):
                self.foo = 'bar'

        class Concrete(B, Interface):
            pass

        self.assertFalse(Concrete._pi.type_is_pure_interface)
        try:
            c = Concrete()
        except Exception as exc:
            self.fail('Instantiation failed {}'.format(exc))

    def test_interface_abc_detection(self):
        @six.add_metaclass(abc.ABCMeta)
        class IABC(object):

            @abc.abstractmethod
            def foo(self):
                pass

            @abc.abstractproperty
            def bar(self):
                return None

        class EmptyABCPI(IABC, Interface):
            pass

        class PIEmptyABC(Interface, IABC):
            pass

        self.assertTrue(EmptyABCPI._pi.type_is_pure_interface)
        self.assertTrue(PIEmptyABC._pi.type_is_pure_interface)
        if six.PY3:
            self.assertTrue('foo' in EmptyABCPI._pi.interface_method_names)
            self.assertTrue('bar' in EmptyABCPI._pi.interface_attribute_names)
        self.assertTrue('foo' in PIEmptyABC._pi.interface_method_names)
        self.assertTrue('bar' in PIEmptyABC._pi.interface_attribute_names)
        with self.assertRaises(InterfaceError):
            EmptyABCPI()
        with self.assertRaises(InterfaceError):
            PIEmptyABC()

    def test_can_use_type_methods(self):
        try:
            class MyInterface(Interface):
                def register(self):
                    pass
        except InterfaceError as exc:
            self.fail(str(exc))

    def test_decorators_not_unwrapped(self):
        def d(f):
            def w():
                return f()
            return w

        with self.assertRaises(InterfaceError):
            class MyInterface(Interface):
                @d
                def foo(self):
                    pass

    def test_can_override_func_with_descriptor(self):
        try:
            class MyDescriptor(object):
                def __init__(self, function):
                    self.__function = function

                def __get__(self, model, cls=None):
                    if model is None:
                        return self
                    else:
                        return self.__function

            class Simple(ISimple, object):
                @MyDescriptor
                def foo():
                    return 1
        except:
            self.fail('Overriding function with descriptor failed')
        s = Simple()
        self.assertEqual(s.foo(), 1)

    def test_missing_methods_warning(self):
        # assemble
        pure_interface.is_development = True
        pure_interface.missing_method_warnings = []
        # act

        class SimpleSimon(ISimple, object):
            pass

        # assert
        self.assertEqual(len(pure_interface.missing_method_warnings), 1)
        msg = pure_interface.missing_method_warnings[0]
        self.assertIn('SimpleSimon', msg)
        self.assertIn('foo', msg)

    def test_inconsistent_mro_warning(self):
        pure_interface.is_development = True

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            class SimpleSimon(object, ISimple):
                def foo(self):
                    pass

        self.assertEqual(warn.call_count, 1)
        self.assertTrue(warn.call_args[0][0].startswith('object should come after ISimple'))

    def test_is_development_flag_stops_warnings(self):
        pure_interface.is_development = False

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            class SimpleSimon(ISimple, object):
                pass

        warn.assert_not_called()

    def test_partial_implementation_attribute(self):
        pure_interface.is_development = True

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            class SimpleSimon(ISimple, object):
                pi_partial_implementation = True

        warn.assert_not_called()

    def test_partial_implementation_warning(self):
        pure_interface.is_development = True

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            class SimpleSimon(ISimple, object):
                pi_partial_implementation = False

        self.assertEqual(warn.call_count, 1)
        self.assertTrue(warn.call_args[0][0].startswith('Partial implementation is indicated'))

    def test_super_class_properties_detected(self):
        class HeightDescr(object):
            height = ADescriptor('really tall')

        class Test(HeightDescr, IPlant):
            pass

        self.assertEqual(frozenset([]), Test._pi.abstractproperties)

    def test_pureinterface_warning(self):
        pure_interface.is_development = True

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            class OldInterface(pure_interface.PureInterface):
                pass

        self.assertEqual(warn.call_count, 1)
        self.assertTrue(warn.call_args[0][0].startswith('PureInterface class has been renamed to Interface'))


class TestPropertyImplementations(unittest.TestCase):
    def test_abstract_property_override_passes(self):
        class Animal(IGrowingAnimal, object):
            def get_height(self):
                return 10

            def set_height(self, height):
                pass

            height = property(get_height, set_height)

        a = Animal()
        self.assertEqual(a.height, 10)

    def test_abstract_attribute_override_passes(self):
        class Animal(IGrowingAnimal, object):
            def __init__(self):
                self.height = 5

            def get_height(self):
                return self.height

            def set_height(self, height):
                pass

        a = Animal()
        self.assertEqual(a.height, 5)

    def test_property_override_passes(self):
        class Plant(IGrowingPlant, object):
            @property
            def height(self):
                return 10

            @height.setter
            def height(self, height):
                pass

        a = Plant()
        self.assertEqual(a.height, 10)

    def test_attribute_override_passes(self):
        class Plant(IGrowingPlant, object):
            def __init__(self):
                self.height = 5

        a = Plant()
        self.assertEqual(a.height, 5)

    def test_ro_abstract_property_override_passes(self):
        class Animal(IAnimal, object):
            @property
            def height(self):
                return 10

        a = Animal()
        self.assertEqual(a.height, 10)

    def test_ro_abstract_property_override_passes3(self):
        class Animal(IAnimal3, object):
            @property
            def height(self):
                return 10

        a = Animal()
        self.assertEqual(a.height, 10)

    def test_ro_abstract_attribute_override_passes(self):
        class Animal(IAnimal, object):
            def __init__(self):
                self.height = 5

        a = Animal()
        self.assertEqual(a.height, 5)

    def test_ro_abstract_attribute_override_passes3(self):
        class Animal(IAnimal3, object):
            def __init__(self):
                self.height = 5

        a = Animal()
        self.assertEqual(a.height, 5)

    def test_ro_property_override_passes(self):
        class Plant(IPlant, object):
            @property
            def height(self):
                return 10

        a = Plant()
        self.assertEqual(a.height, 10)

    def test_ro_attribute_override_passes(self):
        class Plant(IPlant, object):
            def __init__(self):
                self.height = 5

        a = Plant()
        self.assertEqual(a.height, 5)

    def test_missing_abstract_property_fails(self):
        class Animal(IAnimal, object):
            pass

        with self.assertRaises(InterfaceError):
            Animal()

    def test_missing_property_fails(self):
        class Plant(IPlant, object):
            pass

        with self.assertRaises(TypeError):
            Plant()

    def test_missing_property_subclass_fails(self):
        class PlantBase(IPlant, object):
            pass

        class Potato(PlantBase):
            pass

        with self.assertRaises(TypeError):
            Potato()

    def test_abstract_property_is_cleared(self):
        class PlantBase(IPlant, object):
            pass

        class Potato(PlantBase):
            @property
            def height(self):
                return 23

        self.assertEqual(Potato._pi.abstractproperties, set())

    def test_getattr_property_passes(self):
        class Plant(IPlant, object):
            def __getattr__(self, item):
                if item == 'height':
                    return 10
                else:
                    raise AttributeError(item)

        a = Plant()
        self.assertEqual(a.height, 10)

    def test_class_and_static_methods(self):
        try:
            class Concrete(IFunkyMethods, object):
                @classmethod
                def acm(cls):
                    return 1

                @classmethod
                def cm(cls):
                    return 2

                @staticmethod
                def asm():
                    return 3

                @staticmethod
                def sm():
                    return 4
        except Exception as exc:
            self.fail(str(exc))


class IAttribute(Interface):
    a = None


class RaisingProperty(IAttribute, object):
    @property
    def a(self):
        raise Exception("Bang")


class TestAttributeImplementations(unittest.TestCase):
    def test_class_attribute_in_interface(self):
        self.assertIn('a', get_interface_attribute_names(IAttribute))

    def test_class_attribute_must_be_none(self):
        with self.assertRaises(InterfaceError):
            class IAttribute2(Interface):
                a = False

    def test_class_attribute_is_removed(self):
        with self.assertRaises(AttributeError):
            b = IAttribute.a

    def test_class_attribute_is_required(self):
        class A(IAttribute, object):
            pass

        with self.assertRaises(InterfaceError):
            a = A()

    def test_class_attribute_in_dir(self):
        self.assertIn('a', dir(IAttribute))

    def test_instance_attribute_passes(self):
        class A(IAttribute, object):
            def __init__(self):
                self.a = 2

        try:
            a = A()
        except Exception as exc:
            self.fail(str(exc))

        self.assertEqual(a.a, 2)

    def test_class_attribute_passes(self):
        class A(IAttribute, object):
            a = 2

        try:
            a = A()
        except Exception as exc:
            self.fail(str(exc))

        self.assertEqual(a.a, 2)

    def test_property_passes(self):
        class A(IAttribute, object):
            @property
            def a(self):
                return 2

        try:
            a = A()
        except Exception as exc:
            self.fail(str(exc))

        self.assertEqual(a.a, 2)

    def test_mock_spec_includes_attrs(self):
        m = mock.MagicMock(spec=IAttribute, instance=True)
        try:
            x = m.a
        except AttributeError:
            self.fail("class attribute not mocked")

    def test_raising_property(self):
        """ Issue 23 """
        try:
            a = RaisingProperty()
        except:
            self.fail('Instantiation with property that raises failed')

    def test_attr_overridden_with_func(self):
        # forgotten @property decorator
        try:
            class Function(IAttribute, object):
                def a(self):
                    return 2

            Function()
        except:
            self.fail('Overriding attribute with function should not crash')

        self.assertEqual(frozenset(), Function._pi.abstractproperties)

    def test_property_not_accessed(self):
        # previously instantiating C failed (issue 65)
        class IA(Interface):
            next = None

        class IOther(IA):
            pass

        class A(IA, object):
            @property
            def next(self):
                raise RuntimeError('property accessed')

        class B(A):
            pass

        class C(B, IOther):
            pass

        C()


class TestCrossImplementations(unittest.TestCase):
    """ test class attributes implemented as properties and vice versa """
    def test_cross_implementations(self):
        class CrossImplementation(ICrossImplementation, object):
            def __init__(self):
                self.a = 1
                self.c = 2

            @property
            def b(self):
                return 3

            @property
            def d(self):
                return 4

        self.assertEqual(frozenset(['a', 'c']), CrossImplementation._pi.abstractproperties)
        self.assertEqual(frozenset(['a', 'b', 'c', 'd']), CrossImplementation._pi.interface_attribute_names)
