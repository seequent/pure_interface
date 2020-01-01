import pure_interface
import gc

import unittest


class IOne(pure_interface.Interface):
    pass


class ITwo(pure_interface.Interface):
    pass


class COne(object):
    pass


class CTwo(object):
    pass


@pure_interface.adapts(COne, IOne)
def foo(x):
    return IOne()


@pure_interface.adapts(CTwo, ITwo)
def foo(x):
    return ITwo()


gc.collect()


class TestWeakref(unittest.TestCase):
    def test_no_weakref_tb(self):
        x = IOne.adapt_or_none(COne())
        self.assertIsNone(x)

    def test_adapter_list_updated(self):
        adapters = pure_interface._get_pi_attribute(IOne, 'adapters')
        self.assertNotIn(COne, adapters)
