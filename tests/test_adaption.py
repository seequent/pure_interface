# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pure_interface

import unittest


class ISpeaker(pure_interface.PureInterface):
    def speak(self, volume):
        pass


class Speaker(object):
    def speak(self, volume):
        return 'speak'


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


class ITopicSpeaker(ISpeaker):
    @property
    def topic(self):
        pass


class TopicSpeaker(Speaker, ITopicSpeaker):
    def __init__(self, topic):
        self.topic = topic


class TestAdaption(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.CHECK_METHOD_SIGNATURES = True
        pure_interface.ADAPT_TO_INTERFACE_ONLY = False

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

    def test_adapt_to_interface_raises(self):
        with self.assertRaises(ValueError):
            pure_interface.adapt_to_interface(None, ISpeaker)

        with self.assertRaises(ValueError):
            pure_interface.adapt_to_interface(Talker4(), ISpeaker)

    def test_adapt_to_interface_or_none(self):
        self.assertIsNone(pure_interface.adapt_to_interface_or_none(None, ISpeaker))
        self.assertIsNone(pure_interface.adapt_to_interface_or_none(Talker4(), ISpeaker))

    def test_adapt_on_class_works(self):
        talker = Talker()
        s = ISpeaker.adapt(talker)

        self.assertTrue(isinstance(s, ISpeaker))
        self.assertEqual(s.speak(4), 'talk')

    def test_filter_adapt(self):
        a_speaker = Speaker()
        a_talker = Talker()
        input = [None, Talker4(), a_talker, a_speaker, 'text']
        # act
        output = list(pure_interface.filter_adapt(input, ISpeaker))
        # assert
        self.assertEqual(len(output), 2)
        self.assertIs(output[1], a_speaker)
        speaker = output[0]
        self.assertIsInstance(speaker, TalkerToSpeaker)
        self.assertIs(speaker._talker, a_talker)


class TestAdaptionToInterfaceOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.CHECK_METHOD_SIGNATURES = True
        pure_interface.ADAPT_TO_INTERFACE_ONLY = True

    def test_wrapping_works(self):
        topic_speaker = TopicSpeaker('Python')
        s = pure_interface.adapt_to_interface(topic_speaker, ITopicSpeaker)

        self.assertIsInstance(s, pure_interface._ImplementationWrapper)
        self.assertIsInstance(s, ITopicSpeaker)
        self.assertEqual(s.speak(5), 'speak')
        self.assertEqual(s.topic, 'Python')

    def test_wrapping_works2(self):
        topic_speaker = TopicSpeaker('Python')
        s = pure_interface.adapt_to_interface(topic_speaker, ISpeaker)

        self.assertIsInstance(s, pure_interface._ImplementationWrapper)
        self.assertIsInstance(s, ISpeaker)
        self.assertNotIsInstance(s, ITopicSpeaker)

    def test_implicit_adapter_passes(self):
        talker = Talker2()
        s = pure_interface.adapt_to_interface(talker, ISpeaker)

        self.assertIsInstance(s, pure_interface._ImplementationWrapper)
        self.assertIsInstance(s, ISpeaker)
        self.assertEqual(s.speak(5), 'talk')

    def test_callable_adapter_passes(self):
        talker = Talker3()
        s = pure_interface.adapt_to_interface(talker, ISpeaker)

        self.assertIsInstance(s, pure_interface._ImplementationWrapper)
        self.assertIsInstance(s, ISpeaker)
        self.assertEqual(s.speak(5), 'talk')

    def test_adapt_to_interface_or_none(self):
        self.assertIsNone(pure_interface.adapt_to_interface_or_none(None, ISpeaker))
        self.assertIsNone(pure_interface.adapt_to_interface_or_none(Talker4(), ISpeaker))

    def test_filter_adapt(self):
        a_speaker = Speaker()
        a_talker = Talker()
        input_list = [None, Talker4(), a_talker, a_speaker, 'text']
        # act
        output = list(pure_interface.filter_adapt(input_list, ISpeaker))
        # assert
        self.assertEqual(len(output), 2)
        wrapped_speaker = output[1]
        self.assertIs(a_speaker, wrapped_speaker._ImplementationWrapper__impl)
        wrapped_speaker = output[0]
        speaker = wrapped_speaker._ImplementationWrapper__impl
        self.assertIsInstance(speaker, TalkerToSpeaker)
        self.assertIs(speaker._talker, a_talker)

