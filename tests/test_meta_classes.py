# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals


import six
import unittest

import pure_interface


class SomeOtherMetaClass(pure_interface.PureInterfaceType):
    def __new__(mcs, name, bases, clsdict):
        cls = pure_interface.PureInterfaceType.__new__(mcs, name, bases, clsdict)
        print('New class', name, 'is interface:', cls._pi.type_is_pure_interface)
        return cls


@six.add_metaclass(SomeOtherMetaClass)
class InnocentBystander(object):
    def method(self):
        pass


class MyInterface(pure_interface.PureInterface):
    def method2(self):
        pass


class SubclassWithInterface(InnocentBystander, MyInterface):
    def method(self):
        pass


class TestMetaClassMixingChecks(unittest.TestCase):
    def test_submeta_class(self):
        try:
            innocent_bystander = InnocentBystander()
            innocent_bystander.method()
        except Exception as exc:
            self.fail('No exception expected. Got\n' + str(exc))

    def test_submeta_class_with_interface(self):
        with self.assertRaises(TypeError):
            SubclassWithInterface()
