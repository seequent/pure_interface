# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from pure_interface import *

import unittest


class TestImplementationChecks(unittest.TestCase):

    def test_annotations(self):
        class IAnnotation(PureInterface):
            a: int

        self.assertIn('a', get_interface_attribute_names(IAnnotation))
        self.assertIn('a', dir(IAnnotation))

    def test_annotations2(self):
        class IAnnotation(PureInterface):
            a: int
            b = None

        self.assertIn('a', get_interface_attribute_names(IAnnotation))
        self.assertIn('b', get_interface_attribute_names(IAnnotation))
