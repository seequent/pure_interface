import unittest

from pure_interface import *
from pure_interface import adapts, AdapterTracker


class ISpeaker(Interface):
    def speak(self, volume):
        pass


class ISleeper(Interface):
    is_asleep = None


class Talker:
    def __init__(self, saying='talk'):
        self._saying = saying

    def talk(self):
        return self._saying


class Sleeper(ISleeper):
    def __init__(self, is_asleep=False):
        self.is_asleep = is_asleep


@adapts(Talker, ISleeper)
def talker_to_sleeper(talker):
    return Sleeper(talker.talk() == 'zzz')


@adapts(Talker)
class TalkerToSpeaker(ISpeaker):
    def __init__(self, talker):
        self._talker = talker

    def speak(self, volume):
        return self._talker.talk()


class TestAdapterTracker(unittest.TestCase):
    def test_adapt_is_same(self):
        tracker = AdapterTracker()
        t = Talker()

        speaker1 = tracker.adapt(t, ISpeaker)
        speaker2 = tracker.adapt(t, ISpeaker)
        self.assertIsInstance(speaker1, ISpeaker)
        self.assertIsInstance(speaker2, ISpeaker)
        self.assertIs(speaker1, speaker2)

    def test_adapt_multiple_interfaces(self):
        tracker = AdapterTracker()
        t = Talker()

        speaker = tracker.adapt(t, ISpeaker)
        sleeper = tracker.adapt(t, ISleeper)
        self.assertIsInstance(speaker, ISpeaker)
        self.assertIsInstance(sleeper, ISleeper)

    def test_adapt_multiple_instances(self):
        tracker = AdapterTracker()
        t1 = Talker('hello')
        t2 = Talker('zzz')

        speaker1 = tracker.adapt(t1, ISpeaker)
        speaker2 = tracker.adapt(t2, ISpeaker)
        self.assertEqual('hello', speaker1.speak(5))
        self.assertEqual('zzz', speaker2.speak(5))

    def test_mapping_factory_is_used(self):
        mocks = []

        def factory():
            mocks.append(dict())
            return mocks[-1]

        tracker = AdapterTracker(mapping_factory=factory)
        t = Talker('hello')

        tracker.adapt(t, ISpeaker)
        self.assertTrue(len(mocks) > 1)

    def test_adapt_or_none_works(self):
        tracker = AdapterTracker()
        t = Talker()

        speaker = tracker.adapt_or_none(t, ISpeaker)

        self.assertIsInstance(speaker, ISpeaker)

    def test_adapt_or_none_returns_none(self):
        tracker = AdapterTracker()

        speaker = tracker.adapt_or_none('hello', ISpeaker)

        self.assertIsNone(speaker)

    def test_clear(self):
        tracker = AdapterTracker()
        t = Talker()
        speaker1 = tracker.adapt_or_none(t, ISpeaker)

        tracker.clear()

        speaker2 = tracker.adapt_or_none(t, ISpeaker)
        self.assertIsNot(speaker1, speaker2)

