import unittest

import pure_interface


class IGrowingThing(pure_interface.Interface):
    def get_height(self):
        return None

    def set_height(self, height):
        pass


class GrowingMixin(object):
    def __init__(self):
        self._height = 10

    def get_height(self):
        return self._height

    def set_height(self, height):
        self._height = height


class BadGrowingMixin(object):
    def __init__(self):
        self._height = 10

    def get_height(self, units):
        return '{} {}'.format(self._height, units)

    def set_height(self, height):
        self._height = height


class IRegisteredInterface(pure_interface.Interface):
    def register(self):  # overrides ABCMeta.register
        return None

    def adapt(self):
        pass

    def provided_by(self, x):
        pass


class RegisteredInterface(IRegisteredInterface):
    def register(self):  # overrides ABCMeta.register
        return "You're all signed up"

    def adapt(self):
        return "You're highly adaptable"

    def provided_by(self, x):
        return False


class X(object):
    pass


class Y(object):
    pass


class TestInheritance(unittest.TestCase):
    def test_bad_mixin_class_is_checked(self):
        pure_interface.set_is_development(True)

        with self.assertRaises(pure_interface.InterfaceError):
            class Growing(BadGrowingMixin, IGrowingThing):
                pass

    def test_ok_mixin_class_passes(self):
        pure_interface.set_is_development(True)

        class Growing(GrowingMixin, IGrowingThing):
            pass

        g = Growing()
        self.assertEqual(g.get_height(), 10)


class TestPIMethodOverrides(unittest.TestCase):
    def test_register_override(self):
        x = RegisteredInterface()
        # act
        v = x.register()

        self.assertEqual("You're all signed up", v)

    def test_register_via_metaclass(self):
        # act
        pure_interface.InterfaceType.register(IRegisteredInterface, Y)

        self.assertIsInstance(Y(), IRegisteredInterface)

    def test_adapt_override(self):
        x = RegisteredInterface()
        # act
        v = x.adapt()

        self.assertEqual("You're highly adaptable", v)

    def test_adapt_via_metaclass(self):
        x = RegisteredInterface()
        # act
        v = pure_interface.InterfaceType.adapt(IRegisteredInterface, x)

        self.assertIsInstance(v, IRegisteredInterface)

    def test_adapt_via_metaclass2(self):
        x = RegisteredInterface()
        # act
        v = pure_interface.InterfaceType.adapt_or_none(IRegisteredInterface, x)

        self.assertIsInstance(v, IRegisteredInterface)
