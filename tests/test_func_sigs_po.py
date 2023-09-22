# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

import pure_interface
from tests import test_func_sigs3


def func1(a, b, /):  # kw only no defaults
    pass


def func2(a, b='b', /):  # pos only with default
    pass


def func3(a, /, b):  # pos only and p_or_kw
    pass


def func4(a, /, b='b'):
    pass


def func5(a, /, b='b', *, c):
    pass


def func6(a, /, *, b='b', c):
    pass


def func7(a, b='b', /, *, c):
    pass


def all_func(*args, **kwargs):
    pass


def no_pos_only(a, b):
    pass


def no_pos_only_rev(b, a):
    pass


def no_args():
    pass


def func_diff_name(a, z='z', /):
    pass


def func1ex(a, b, c='c', /):
    pass


def func1ex2(b, /, a):
    pass


def func3ex(a, b, c='c'):
    pass


def func3ex2(a, b, c, d='d'):
    pass


def func5ex(a, b='b', /, *, c='c'):
    pass


def func5ex2(a, b='b', c='c'):
    pass


class TestFunctionSigsPositionalOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.set_is_development(True)

    def check_signatures(self, int_func, impl_func, expected_result):
        reality = test_func_sigs3.test_call(int_func, impl_func)
        self.assertEqual(expected_result, reality,
                         '{}, {}. Reality does not match expectations'.format(int_func.__name__, impl_func.__name__))
        interface_sig = pure_interface.interface.signature(int_func)
        concrete_sig = pure_interface.interface.signature(impl_func)
        result = pure_interface.interface._signatures_are_consistent(concrete_sig, interface_sig)
        self.assertEqual(expected_result, result,
                         '{}, {}. Signature test gave wrong answer'.format(int_func.__name__, impl_func.__name__))

    def test_pos_only(self):
        self.check_signatures(func1, func2, True)
        self.check_signatures(func1, func3, True)
        self.check_signatures(func1, func4, True)
        self.check_signatures(func1, func5, False)
        self.check_signatures(func1, all_func, True)
        self.check_signatures(func1, no_pos_only, True)
        self.check_signatures(func1, no_pos_only_rev, True)
        self.check_signatures(func1, no_args, False)
        self.check_signatures(func1, func_diff_name, True)
        self.check_signatures(func1, func1ex, True)
        self.check_signatures(func1, func1ex2, True)
        self.check_signatures(func3, func3ex, True)
        self.check_signatures(func3, func3ex2, False)
        self.check_signatures(func5, func5ex, False)
        self.check_signatures(func5, func5ex2, True)
