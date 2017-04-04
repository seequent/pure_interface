# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

import pure_interface


class IGrowingThing(pure_interface.PureInterface):
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


class TestInheritance(unittest.TestCase):
    def test_bad_mixin_class_is_checked(self):
        pure_interface.CHECK_METHOD_SIGNATURES = True

        with self.assertRaises(pure_interface.InterfaceError):
            class Growing(BadGrowingMixin, IGrowingThing):
                pass

    def test_ok_mixin_class_passes(self):
        pure_interface.CHECK_METHOD_SIGNATURES = True

        class Growing(GrowingMixin, IGrowingThing):
            pass

        g = Growing()
        self.assertEqual(g.get_height(), 10)
