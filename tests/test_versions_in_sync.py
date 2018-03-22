# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import unittest
import pure_interface


class TestVersionsMatch(unittest.TestCase):
    def test_versions(self):
        setup_py = os.path.join(os.path.dirname(__file__), '..', 'setup.py')
        with open(setup_py, 'rU') as f:
            setup_contents = f.readlines()

        for line in setup_contents:
            if 'version=' in line:
                self.assertIn(pure_interface.__version__, line)
                break
        else:
            self.fail('did not find version in setup.py')
