import pure_interface

import unittest


class IAnimal(pure_interface.PureInterface):
    def get_height(self):
        return None

    def set_height(self, height):
        pass

    height = pure_interface.abstractproperty(get_height, set_height)


class IPlant(pure_interface.PureInterface):
    @property
    def height(self):
        return None

    @height.setter
    def height(self, height):
        pass


class TestPropertyImplementations(unittest.TestCase):
    def test_abstract_property_override_passes(self):
        class Animal(IAnimal):
            @property
            def height(self):
                return 10

            @height.setter
            def height(self, height):
                pass

        a = Animal()
        self.assertEqual(a.height, 10)

    def test_abstract_attribute_override_passes(self):
        class Animal(IAnimal):
            def __init__(self):
                self.height = 5

        a = Animal()
        self.assertEqual(a.height, 5)

