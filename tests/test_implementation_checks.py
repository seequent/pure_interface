import pure_interface
from pure_interface import *

import abc
import unittest

import six

try:
    from unittest import mock
except ImportError:
    import mock


class IAnimal(PureInterface):
    @abstractproperty
    def height(self):
        return None


class IAnimal3(PureInterface):
    # python 3 style syntax
    @property
    @abstractmethod
    def height(self):
        pass

    @height.setter
    @abstractmethod
    def height(self, height):
        pass


class IGrowingAnimal(PureInterface):
    def get_height(self):
        return None

    def set_height(self, height):
        pass

    height = abc.abstractproperty(get_height, set_height)


class IPlant(PureInterface):
    @property
    def height(self):
        return None


class IGrowingPlant(PureInterface):
    @property
    def height(self):
        return None

    @height.setter
    def height(self, height):
        pass


class IFunkyMethods(PureInterface):
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


class ISimple(PureInterface):
    def foo(self):
        pass


class ICrossImplementation(PureInterface):
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
            PureInterface()
        with self.assertRaises(InterfaceError) as exc:
            IPlant()
        assert 'Interfaces cannot be instantiated' in str(exc.exception)
        with self.assertRaises(InterfaceError):
            IAnimal()
        with self.assertRaises(InterfaceError):
            IAnimal3()

    def test_concrete_base_detection(self):
        class Concrete(object, PureInterface):
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

        class Concrete(B, PureInterface):
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

        class Concrete(B, PureInterface):
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

        class EmptyABCPI(IABC, PureInterface):
            pass

        class PIEmptyABC(PureInterface, IABC):
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
            class MyInterface(PureInterface):
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
            class MyInterface(PureInterface):
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

            class Simple(object, ISimple):
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

        class SimpleSimon(object, ISimple):
            pass

        # assert
        self.assertEqual(len(pure_interface.missing_method_warnings), 1)
        msg = pure_interface.missing_method_warnings[0]
        self.assertIn('SimpleSimon', msg)
        self.assertIn('foo', msg)

    def test_is_development_flag_stops_warnings(self):
        pure_interface.is_development = False

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            class SimpleSimon(object, ISimple):
                pass

        warn.assert_not_called()

    def test_partial_implementation_attribute(self):
        pure_interface.is_development = True

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            class SimpleSimon(object, ISimple):
                pi_partial_implementation = True

        warn.assert_not_called()

    def test_partial_implementation_warning(self):
        pure_interface.is_development = True

        warn = mock.MagicMock()
        with mock.patch('warnings.warn', warn):
            class SimpleSimon(object, ISimple):
                pi_partial_implementation = False

        self.assertEqual(warn.call_count, 1)
        self.assertTrue(warn.call_args[0][0].startswith('Partial implmentation is indicated'))


class TestPropertyImplementations(unittest.TestCase):
    def test_abstract_property_override_passes(self):
        class Animal(object, IGrowingAnimal):
            def get_height(self):
                return 10

            def set_height(self, height):
                pass

            height = property(get_height, set_height)

        a = Animal()
        self.assertEqual(a.height, 10)

    def test_abstract_attribute_override_passes(self):
        class Animal(object, IGrowingAnimal):
            def __init__(self):
                self.height = 5

            def get_height(self):
                return self.height

            def set_height(self, height):
                pass

        a = Animal()
        self.assertEqual(a.height, 5)

    def test_property_override_passes(self):
        class Plant(object, IGrowingPlant):
            @property
            def height(self):
                return 10

            @height.setter
            def height(self, height):
                pass

        a = Plant()
        self.assertEqual(a.height, 10)

    def test_attribute_override_passes(self):
        class Plant(object, IGrowingPlant):
            def __init__(self):
                self.height = 5

        a = Plant()
        self.assertEqual(a.height, 5)

    def test_ro_abstract_property_override_passes(self):
        class Animal(object, IAnimal):
            @property
            def height(self):
                return 10

        a = Animal()
        self.assertEqual(a.height, 10)

    def test_ro_abstract_property_override_passes3(self):
        class Animal(object, IAnimal3):
            @property
            def height(self):
                return 10

        a = Animal()
        self.assertEqual(a.height, 10)

    def test_ro_abstract_attribute_override_passes(self):
        class Animal(object, IAnimal):
            def __init__(self):
                self.height = 5

        a = Animal()
        self.assertEqual(a.height, 5)

    def test_ro_abstract_attribute_override_passes3(self):
        class Animal(object, IAnimal3):
            def __init__(self):
                self.height = 5

        a = Animal()
        self.assertEqual(a.height, 5)

    def test_ro_property_override_passes(self):
        class Plant(object, IPlant):
            @property
            def height(self):
                return 10

        a = Plant()
        self.assertEqual(a.height, 10)

    def test_ro_attribute_override_passes(self):
        class Plant(object, IPlant):
            def __init__(self):
                self.height = 5

        a = Plant()
        self.assertEqual(a.height, 5)

    def test_missing_abstract_property_fails(self):
        class Animal(object, IAnimal):
            pass

        with self.assertRaises(InterfaceError):
            Animal()

    def test_missing_property_fails(self):
        class Plant(object, IPlant):
            pass

        with self.assertRaises(TypeError):
            Plant()

    def test_missing_property_subclass_fails(self):
        class PlantBase(object, IPlant):
            pass

        class Potato(PlantBase):
            pass

        with self.assertRaises(TypeError):
            Potato()

    def test_abstract_property_is_cleared(self):
        class PlantBase(object, IPlant):
            pass

        class Potato(PlantBase):
            @property
            def height(self):
                return 23

        self.assertEqual(Potato._pi.abstractproperties, set())

    def test_getattr_property_passes(self):
        class Plant(object, IPlant):
            def __getattr__(self, item):
                if item == 'height':
                    return 10
                else:
                    raise AttributeError(item)

        a = Plant()
        self.assertEqual(a.height, 10)

    def test_class_and_static_methods(self):
        try:
            class Concrete(object, IFunkyMethods):
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


class IAttribute(PureInterface):
    a = None


class RaisingProperty(object, IAttribute):
    @property
    def a(self):
        raise Exception("Bang")


class TestAttributeImplementations(unittest.TestCase):
    def test_class_attribute_in_interface(self):
        self.assertIn('a', get_interface_attribute_names(IAttribute))

    def test_class_attribute_must_be_none(self):
        with self.assertRaises(InterfaceError):
            class IAttribute2(PureInterface):
                a = False

    def test_class_attribute_is_removed(self):
        with self.assertRaises(AttributeError):
            b = IAttribute.a

    def test_class_attribute_is_required(self):
        class A(object, IAttribute):
            pass

        with self.assertRaises(InterfaceError):
            a = A()

    def test_class_attribute_in_dir(self):
        self.assertIn('a', dir(IAttribute))

    def test_instance_attribute_passes(self):
        class A(object, IAttribute):
            def __init__(self):
                self.a = 2

        try:
            a = A()
        except Exception as exc:
            self.fail(str(exc))

        self.assertEqual(a.a, 2)

    def test_class_attribute_passes(self):
        class A(object, IAttribute):
            a = 2

        try:
            a = A()
        except Exception as exc:
            self.fail(str(exc))

        self.assertEqual(a.a, 2)

    def test_property_passes(self):
        class A(object, IAttribute):
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
            class Function(Concrete, IAttribute):
                def a(self):
                    return 2

            Function()
        except:
            self.fail('Overriding attribute with function should not crash')

        self.assertEqual(frozenset(), Function._pi.abstractproperties)


class TestCrossImplementations(unittest.TestCase):
    """ test class attributes implemented as properties and vice versa """
    def test_cross_implementations(self):
        class CrossImplementation(Concrete, ICrossImplementation):
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
