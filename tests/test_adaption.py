# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pure_interface

import unittest


class ISpeaker(pure_interface.PureInterface):
    def speak(self, volume):
        pass


class Talker(object):
    def talk(self):
        return 'talk'


@pure_interface.adapts(Talker, ISpeaker)
class TalkerToSpeaker(object, ISpeaker):
    def __init__(self, talker):
        self._talker = talker

    def speak(self, volume):
        return self._talker.talk()


class Talker2(object):
    def talk(self):
        return 'talk'


@pure_interface.adapts(Talker2, ISpeaker)
class TalkerToSpeaker2(object):
    def __init__(self, talker):
        self._talker = talker

    def speak(self, volume):
        return self._talker.talk()


class TalkerToSpeaker3(object):
    def __init__(self, talker):
        self._talker = talker

    def speak(self, volume):
        return self._talker.talk()


class Talker3(object):
    def talk(self):
        return 'talk'


@pure_interface.adapts(Talker3, ISpeaker)
def talk_to_speaker(talker):
    return TalkerToSpeaker(talker)


class Talker4(object):
    def talk(self):
        return 'talk'


def bad_adapter(talker):
    return talker


class TestAdaption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.CHECK_METHOD_SIGNATURES = True

    def test_adaption_passes(self):
        talker = Talker()
        s = pure_interface.adapt_to_interface(talker, ISpeaker)

        self.assertTrue(isinstance(s, ISpeaker))
        self.assertEqual(s.speak(5), 'talk')

    def test_implicit_adapter_passes(self):
        talker = Talker2()
        s = pure_interface.adapt_to_interface(talker, ISpeaker)

        self.assertTrue(isinstance(s, ISpeaker))
        self.assertEqual(s.speak(5), 'talk')

    def test_callable_adapter_passes(self):
        talker = Talker3()
        s = pure_interface.adapt_to_interface(talker, ISpeaker)

        self.assertTrue(isinstance(s, ISpeaker))
        self.assertEqual(s.speak(5), 'talk')

    def test_adapter_call_check(self):
        pure_interface.register_adapter(bad_adapter, Talker4, ISpeaker)
        talker = Talker4()
        with self.assertRaises(ValueError):
            pure_interface.adapt_to_interface(talker, ISpeaker)

    def test_adapter_check(self):
        with self.assertRaises(ValueError):
            pure_interface.register_adapter(5, Talker, ISpeaker)

    def test_from_type_check(self):
        with self.assertRaises(ValueError):  # must be callable
            pure_interface.register_adapter(TalkerToSpeaker3, 6, ISpeaker)

        with self.assertRaises(ValueError):  # not None type
            pure_interface.register_adapter(TalkerToSpeaker3, type(None), ISpeaker)

        with self.assertRaises(ValueError):  # already adapted
            pure_interface.register_adapter(TalkerToSpeaker, Talker, ISpeaker)

    def test_to_interface_check(self):
        with self.assertRaises(ValueError):  # to_interface is an interface
            pure_interface.register_adapter(TalkerToSpeaker3, Talker, Talker)

        with self.assertRaises(ValueError):  # to_interface is not concrete
            pure_interface.register_adapter(TalkerToSpeaker3, Talker, TalkerToSpeaker)
