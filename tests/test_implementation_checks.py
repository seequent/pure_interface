import pure_interface

import abc
import unittest

import six


class IAnimal(pure_interface.PureInterface):
    @pure_interface.abstractproperty
    def height(self):
        return None


class IGrowingAnimal(pure_interface.PureInterface):
    def get_height(self):
        return None

    def set_height(self, height):
        pass

    height = pure_interface.abstractproperty(get_height, set_height)


class IPlant(pure_interface.PureInterface):
    @property
    def height(self):
        return None


class IGrowingPlant(pure_interface.PureInterface):
    @property
    def height(self):
        return None

    @height.setter
    def height(self, height):
        pass


class IFunkyMethods(pure_interface.PureInterface):
    @pure_interface.abstractclassmethod
    def acm(cls):
        return None

    @classmethod
    def cm(cls):
        return None

    @pure_interface.abstractstaticmethod
    def asm():
        return None

    @staticmethod
    def sm():
        return None


class ISimple(pure_interface.PureInterface):
    def foo(self):
        pass


class TestImplementationChecks(unittest.TestCase):
    def test_instantiation_fails(self):
        with self.assertRaises(TypeError):
            pure_interface.PureInterface()
        with self.assertRaises(TypeError) as exc:
            IPlant()
        assert 'Interfaces cannot be instantiated' in str(exc.exception)
        with self.assertRaises(TypeError):
            IAnimal()

    def test_concrete_base_detection(self):
        class Concrete(object, pure_interface.PureInterface):
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

        class Concrete(B, pure_interface.PureInterface):
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

        class Concrete(B, pure_interface.PureInterface):
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

        class EmptyABCPI(IABC, pure_interface.PureInterface):
            pass

        class PIEmptyABC(pure_interface.PureInterface, IABC):
            pass

        self.assertTrue(EmptyABCPI._pi.type_is_pure_interface)
        self.assertTrue(PIEmptyABC._pi.type_is_pure_interface)
        if six.PY3:
            self.assertTrue('foo' in EmptyABCPI._pi.interface_method_names)
            self.assertTrue('bar' in EmptyABCPI._pi.interface_property_names)
        self.assertTrue('foo' in PIEmptyABC._pi.interface_method_names)
        self.assertTrue('bar' in PIEmptyABC._pi.interface_property_names)
        with self.assertRaises(TypeError):
            EmptyABCPI()
        with self.assertRaises(TypeError):
            PIEmptyABC()

    def test_can_use_type_methods(self):
        try:
            class MyInterface(pure_interface.PureInterface):
                def register(self):
                    pass
        except pure_interface.InterfaceError as exc:
            self.fail(str(exc))

    def test_decorators_not_unwrapped(self):
        def d(f):
            def w():
                return f()
            return w

        with self.assertRaises(pure_interface.InterfaceError):
            class MyInterface(pure_interface.PureInterface):
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

    def test_missing_methods(self):
        class SimpleSimon(object, ISimple):
            pass
        for msg in pure_interface.missing_method_warnings:
            if 'SimpleSimon' in msg:
                self.assertIn('foo', msg)
                break
        else:
            self.fail('No missing method message for SimpleSimon.foo')


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

    def test_ro_abstract_attribute_override_passes(self):
        class Animal(object, IAnimal):
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

        with self.assertRaises(TypeError):
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
