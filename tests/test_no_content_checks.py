import abc
import pure_interface

import unittest

import pure_interface.errors


class TestNoContentChecks(unittest.TestCase):
    def test_empty_function_passes(self):
        class IAnimal(pure_interface.Interface):
            def speak(self, volume):
                pass

            def move(self, to):
                """ a comment """
                pass

            def sleep(self, duration):
                "a comment"

            @property
            @abc.abstractmethod
            def weight(self):
                pass

            @property
            def height(self):
                """A comment"""
                return None

            @height.setter
            def height(self, height):
                pass

    def test_raise_function_passes(self):
        class IAnimal(pure_interface.Interface):
            def speak(self, volume):
                raise NotImplementedError()

            def move(self, to):
                """ a comment """
                raise NotImplementedError('subclass must provide')

            def sleep(self, duration):
                """a comment"""
                msg = 'msg {}'.format(self.__class__.__name__)
                raise NotImplementedError(msg)

    def test_async_function_passes(self):
        class IAnimal(pure_interface.Interface):
            async def speak(self, volume):
                pass

            async def move(self, to):
                """ a comment """
                raise NotImplementedError('subclass must provide')

            async def sleep(self, duration):
                """a comment"""
                pass

    def test_raise_other_fails(self):
        with self.assertRaises(pure_interface.InterfaceError):
            class INotAnimal(pure_interface.Interface):
                def bad_method(self):
                    """a comment"""
                    msg = 'msg {}'.format(self.__class__.__name__)
                    raise RuntimeError(msg)

    def test_function_with_body_fails(self):
        with self.assertRaises(pure_interface.errors.InterfaceError):
            class IAnimal(pure_interface.Interface):
                def speak(self, volume):
                    if volume > 0:
                        print('hello' + '!' * int(volume))

    def test_abstract_function_with_body_fails(self):
        with self.assertRaises(pure_interface.errors.InterfaceError):
            class IAnimal(pure_interface.Interface):
                @abc.abstractmethod
                def speak(self, volume):
                    if volume > 0:
                        print('hello' + '!' * int(volume))

    def test_abstract_classmethod_with_body_fails(self):
        with self.assertRaises(pure_interface.errors.InterfaceError):
            class IAnimal(pure_interface.Interface):
                @classmethod
                @abc.abstractmethod
                def speak(cls, volume):
                    if volume > 0:
                        print('hello' + '!' * int(volume))

    def test_property_with_body_fails(self):
        with self.assertRaises(pure_interface.errors.InterfaceError):
            class IAnimal(pure_interface.Interface):
                @property
                def height(self):
                    return self
