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


@pure_interface.adapts(Talker)
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


@pure_interface.adapts(type(None), ISpeaker)
def none_to_speaker(_none):  # Speaker implicitly supplies ISpeaker
    return Speaker()


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
        pure_interface.is_development = True

    def test_adaption_passes(self):
        talker = Talker()
        s = ISpeaker.adapt(talker, interface_only=False)

        self.assertTrue(ISpeaker.provided_by(s, allow_implicit=False))
        self.assertEqual(s.speak(5), 'talk')

    def test_implicit_adapter(self):
        talker = Talker2()
        s = ISpeaker.adapt_or_none(talker, interface_only=False)
        self.assertIsNone(s)

        s = ISpeaker.adapt_or_none(talker, allow_implicit=True, interface_only=False)
        self.assertTrue(ISpeaker.provided_by(s, allow_implicit=True))
        self.assertEqual(s.speak(5), 'talk')

    def test_callable_adapter_passes(self):
        talker = Talker3()
        s = ISpeaker.adapt(talker, interface_only=False)

        self.assertTrue(ISpeaker.provided_by(s, allow_implicit=False))
        self.assertEqual(s.speak(5), 'talk')

    def test_adapter_call_check(self):
        pure_interface.register_adapter(bad_adapter, Talker4, ISpeaker)
        talker = Talker4()
        with self.assertRaises(ValueError):
            ISpeaker.adapt(talker, interface_only=False)

    def test_adapter_check(self):
        with self.assertRaises(ValueError):
            pure_interface.register_adapter(5, Talker, ISpeaker)

    def test_from_type_check(self):
        with self.assertRaises(ValueError):  # must be callable
            pure_interface.register_adapter(TalkerToSpeaker3, 6, ISpeaker)

        with self.assertRaises(ValueError):  # already adapted
            pure_interface.register_adapter(TalkerToSpeaker, Talker, ISpeaker)

    def test_to_interface_check(self):
        with self.assertRaises(ValueError):  # to_interface is an interface
            pure_interface.register_adapter(TalkerToSpeaker3, Talker, Talker)

        with self.assertRaises(ValueError):  # to_interface is not concrete
            pure_interface.register_adapter(TalkerToSpeaker3, Talker, TalkerToSpeaker)

    def test_adapt_to_interface_raises(self):
        with self.assertRaises(ValueError):
            ISpeaker.adapt(None, interface_only=False)

        with self.assertRaises(ValueError):
            ISpeaker.adapt(Talker4(), interface_only=False)

    def test_adapt_to_interface_or_none(self):
        self.assertIsNone(ISpeaker.adapt_or_none(None, interface_only=False))
        self.assertIsNone(ISpeaker.adapt_or_none(Talker4(), interface_only=False))

    def test_no_interface_on_class_raises(self):
        with self.assertRaises(pure_interface.InterfaceError):
            @pure_interface.adapts(ISpeaker)
            class NoInterface(object):
                pass

    def test_adapt_on_class_works(self):
        talker = Talker()
        s = ISpeaker.adapt(talker, interface_only=False)

        self.assertTrue(ISpeaker.provided_by(s, allow_implicit=False))
        self.assertEqual(s.speak(4), 'talk')

    def test_filter_adapt(self):
        a_speaker = Speaker()
        a_talker = Talker()
        input = [None, Talker4(), a_talker, a_speaker, 'text']
        # act
        output = list(ISpeaker.filter_adapt(input, interface_only=False))
        # assert
        self.assertEqual(len(output), 1)
        speaker = output[0]
        self.assertIsInstance(speaker, TalkerToSpeaker)
        self.assertIs(speaker._talker, a_talker)

    def test_implicit_filter_adapt(self):
        a_speaker = Speaker()
        a_talker = Talker()
        input = [None, Talker4(), a_talker, a_speaker, 'text']
        # act
        output = list(ISpeaker.filter_adapt(input, allow_implicit=True, interface_only=False))
        # assert
        self.assertEqual(len(output), 3)
        self.assertIsInstance(output[0], Speaker)
        speaker = output[1]
        self.assertIs(output[2], a_speaker)
        self.assertIsInstance(speaker, TalkerToSpeaker)
        self.assertIs(speaker._talker, a_talker)


class TestAdaptionToInterfaceOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.is_development = True

    def test_wrapping_works(self):
        topic_speaker = TopicSpeaker('Python')
        s = ITopicSpeaker.adapt(topic_speaker)
        topic_speaker2 = TopicSpeaker('Interfaces')
        t = ITopicSpeaker.adapt(topic_speaker2)

        self.assertIsInstance(s, pure_interface._ImplementationWrapper)
        self.assertIsInstance(s, ITopicSpeaker)
        self.assertEqual(s.speak(5), 'speak')
        self.assertEqual(s.topic, 'Python')
        self.assertEqual(t.topic, 'Interfaces')

    def test_wrapping_works2(self):
        topic_speaker = TopicSpeaker('Python')
        s = ISpeaker.adapt(topic_speaker)

        self.assertIsInstance(s, pure_interface._ImplementationWrapper)
        self.assertIsInstance(s, ISpeaker)
        self.assertNotIsInstance(s, ITopicSpeaker)
        with self.assertRaises(AttributeError):
            s.topic

    def test_implicit_adapter_passes(self):
        talker = Talker2()
        s = ISpeaker.adapt(talker, allow_implicit=True)

        self.assertIsInstance(s, pure_interface._ImplementationWrapper)
        self.assertIsInstance(s, ISpeaker)
        self.assertEqual(s.speak(5), 'talk')

    def test_callable_adapter_passes(self):
        talker = Talker3()
        s = ISpeaker.adapt(talker)

        self.assertIsInstance(s, pure_interface._ImplementationWrapper)
        self.assertIsInstance(s, ISpeaker)
        self.assertEqual(s.speak(5), 'talk')

    def test_adapt_to_interface_or_none(self):
        self.assertIsNone(ISpeaker.adapt_or_none(None))
        self.assertIsNone(ISpeaker.adapt_or_none(Talker4()))

    def test_filter_adapt(self):
        a_speaker = Speaker()
        a_talker = Talker()
        input_list = [None, Talker4(), a_talker, a_speaker, 'text']
        # act
        output = list(ISpeaker.filter_adapt(input_list))
        # assert
        self.assertEqual(len(output), 1)

    def test_implicit_filter_adapt(self):
        a_speaker = Speaker()
        a_talker = Talker()
        input_list = [None, Talker4(), a_talker, a_speaker, 'text']
        # act
        output = list(ISpeaker.filter_adapt(input_list, allow_implicit=True))
        # assert
        self.assertEqual(len(output), 3)
        wrapped_speaker = output[0]
        self.assertIsInstance(wrapped_speaker._ImplementationWrapper__impl, Speaker)
        wrapped_speaker = output[2]
        self.assertIs(a_speaker, wrapped_speaker._ImplementationWrapper__impl)
        wrapped_speaker = output[1]
        speaker = wrapped_speaker._ImplementationWrapper__impl
        self.assertIsInstance(speaker, TalkerToSpeaker)
        self.assertIs(speaker._talker, a_talker)
