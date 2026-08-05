# --------------------------------------------------------------------------------------------
#  Copyright (c) 2024 Bentley Systems, Incorporated. All rights reserved.
# --------------------------------------------------------------------------------------------

import unittest
from unittest import mock

import pure_interface
from pure_interface import Interface, interface
from pure_interface.adaption import register_adapter


class IAnimal(Interface):
    def speak(self):
        pass


class IDog(IAnimal, Interface):
    def fetch(self):
        pass


class ICreature(Interface):
    """Separate interface used to test cache invalidation via .register()."""

    def speak(self):
        pass


class Cat:
    pass


class CatToIAnimal(IAnimal):
    def __init__(self, obj):
        pass

    def speak(self):
        return "meow"


class Hawk:
    pass


class HawkToIDog(IDog):
    def __init__(self, obj):
        pass

    def speak(self):
        return "screech"

    def fetch(self):
        return "prey"


class Fish:
    pass  # used to test None caching and late adapter registration


class FishToIAnimal(IAnimal):
    def __init__(self, obj):
        pass

    def speak(self):
        return "blub"


class FishToIDog(IDog):
    def __init__(self, obj):
        pass

    def speak(self):
        return "blub"

    def fetch(self):
        return "swim"


class Iguana:
    pass  # used for register() test


ICreature.register(IAnimal)


def _register_adapters():
    register_adapter(CatToIAnimal, Cat, IAnimal)
    register_adapter(HawkToIDog, Hawk, IDog)


class TestAdapterCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.set_is_development(True)

    def setUp(self):
        _register_adapters()

    def tearDown(self):
        IAnimal._pi.adapter_cache.clear()
        IDog._pi.adapter_cache.clear()
        ICreature._pi.adapter_cache.clear()
        IAnimal._pi.adapters.clear()
        IDog._pi.adapters.clear()

    def test_adapter_cached_after_adapt(self):
        IAnimal.adapt(Cat(), interface_only=False)
        self.assertIn(Cat, IAnimal._pi.adapter_cache)
        self.assertIs(IAnimal._pi.adapter_cache[Cat], CatToIAnimal)

    def test_get_adapter_called_only_once_for_repeated_adapts(self):
        cat = Cat()
        with mock.patch("pure_interface.interface._get_adapter", wraps=interface._get_adapter) as mock_get:
            IAnimal.adapt(cat, interface_only=False)
            IAnimal.adapt(cat, interface_only=False)
        mock_get.assert_called_once()

    def test_none_cached_when_no_adapter_exists(self):
        IAnimal.adapt_or_none(Fish(), interface_only=False)
        self.assertIn(Fish, IAnimal._pi.adapter_cache)
        self.assertIsNone(IAnimal._pi.adapter_cache[Fish])

    def test_get_adapter_called_only_once_for_repeated_none_results(self):
        fish = Fish()
        with mock.patch("pure_interface.interface._get_adapter", wraps=interface._get_adapter) as mock_get:
            IAnimal.adapt_or_none(fish, interface_only=False)
            IAnimal.adapt_or_none(fish, interface_only=False)
        mock_get.assert_called_once()

    def test_clear_adapter_caches_clears_interface_cache(self):
        IAnimal._pi.adapter_cache[Cat] = CatToIAnimal
        interface.clear_adapter_caches(IAnimal)
        self.assertEqual(len(IAnimal._pi.adapter_cache), 0)

    def test_clear_adapter_caches_on_child_clears_parent_cache(self):
        # IAnimal's cache should be cleared when IDog's adapters change,
        # because _get_adapter(IAnimal, ...) collects adapters from IAnimal.__subclasses__()
        IAnimal._pi.adapter_cache[Hawk] = None
        interface.clear_adapter_caches(IDog)
        self.assertNotIn(Hawk, IAnimal._pi.adapter_cache)

    def test_parent_interface_finds_adapter_registered_on_child(self):
        adapted = IAnimal.adapt(Hawk(), interface_only=False)
        self.assertIsInstance(adapted, HawkToIDog)

    def test_parent_caches_adapter_found_via_child(self):
        IAnimal.adapt(Hawk(), interface_only=False)
        self.assertIn(Hawk, IAnimal._pi.adapter_cache)
        self.assertIs(IAnimal._pi.adapter_cache[Hawk], HawkToIDog)

    def test_register_type_clears_cache(self):
        IAnimal._pi.adapter_cache[Iguana] = None
        IAnimal.register(Iguana)
        self.assertNotIn(Iguana, IAnimal._pi.adapter_cache)

    def test_register_adapter_clears_entire_cache(self):
        # Pre-populate cache with an unrelated entry
        IAnimal._pi.adapter_cache[Fish] = None
        # Registering any adapter should wipe the whole cache
        register_adapter(lambda obj: CatToIAnimal(obj), Iguana, IAnimal)
        self.assertEqual(len(IAnimal._pi.adapter_cache), 0)

    def test_stale_none_on_parent_cleared_when_adapter_registered_on_child(self):
        # Prime a stale None on both parent and child: no adapter for Fish yet
        self.assertIsNone(IAnimal.adapt_or_none(Fish(), interface_only=False))
        self.assertIsNone(IDog.adapt_or_none(Fish(), interface_only=False))
        self.assertIsNone(IAnimal._pi.adapter_cache[Fish])
        self.assertIsNone(IDog._pi.adapter_cache[Fish])

        # Registering on the child must evict the stale entry from both caches
        register_adapter(FishToIDog, Fish, IDog)
        self.assertNotIn(Fish, IAnimal._pi.adapter_cache)
        self.assertNotIn(Fish, IDog._pi.adapter_cache)

        # Parent can now adapt Fish via the child's adapter
        adapted = IAnimal.adapt(Fish(), interface_only=False)
        self.assertIsInstance(adapted, FishToIDog)

    def test_stale_none_cleared_when_adapter_added_to_registered_interface(self):
        # IAnimal is registered as a virtual subclass of ICreature at module level.
        # _get_adapter(ICreature, T) therefore reads IAnimal._pi.adapters.
        # If a stale None is cached on ICreature and a new adapter is later added
        # to IAnimal, the stale entry must be evicted so ICreature can find the adapter.

        # Prime ICreature's cache with None — no adapter for Fish exists yet
        self.assertIsNone(ICreature.adapt_or_none(Fish(), interface_only=False))
        self.assertIn(Fish, ICreature._pi.adapter_cache)
        self.assertIsNone(ICreature._pi.adapter_cache[Fish])

        # Register an adapter for Fish on IAnimal
        register_adapter(FishToIAnimal, Fish, IAnimal)

        # ICreature's stale None should have been evicted
        self.assertNotIn(Fish, ICreature._pi.adapter_cache)

        # ICreature should now successfully adapt Fish via IAnimal's adapter
        adapted = ICreature.adapt(Fish(), interface_only=False)
        self.assertIsInstance(adapted, FishToIAnimal)
