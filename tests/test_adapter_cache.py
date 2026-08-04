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
    pass  # never adapted — used to test None caching


class Iguana:
    pass  # used for register() test


class TestAdapterCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pure_interface.set_is_development(True)
        register_adapter(CatToIAnimal, Cat, IAnimal)
        register_adapter(HawkToIDog, Hawk, IDog)

    def setUp(self):
        IAnimal._pi._adapter_cache.clear()
        IDog._pi._adapter_cache.clear()

    def test_adapter_cached_after_adapt(self):
        IAnimal.adapt(Cat(), interface_only=False)
        self.assertIn(Cat, IAnimal._pi._adapter_cache)
        self.assertIs(IAnimal._pi._adapter_cache[Cat], CatToIAnimal)

    def test_get_adapter_called_only_once_for_repeated_adapts(self):
        cat = Cat()
        with mock.patch("pure_interface.interface._get_adapter", wraps=interface._get_adapter) as mock_get:
            IAnimal.adapt(cat, interface_only=False)
            IAnimal.adapt(cat, interface_only=False)
        mock_get.assert_called_once()

    def test_none_cached_when_no_adapter_exists(self):
        IAnimal.adapt_or_none(Fish(), interface_only=False)
        self.assertIn(Fish, IAnimal._pi._adapter_cache)
        self.assertIsNone(IAnimal._pi._adapter_cache[Fish])

    def test_get_adapter_called_only_once_for_repeated_none_results(self):
        fish = Fish()
        with mock.patch("pure_interface.interface._get_adapter", wraps=interface._get_adapter) as mock_get:
            IAnimal.adapt_or_none(fish, interface_only=False)
            IAnimal.adapt_or_none(fish, interface_only=False)
        mock_get.assert_called_once()

    def test_clear_adapter_caches_clears_interface_cache(self):
        IAnimal._pi._adapter_cache[Cat] = CatToIAnimal
        interface.clear_adapter_caches(IAnimal)
        self.assertEqual(IAnimal._pi._adapter_cache, {})

    def test_clear_adapter_caches_on_child_clears_parent_cache(self):
        # IAnimal's cache should be cleared when IDog's adapters change,
        # because _get_adapter(IAnimal, ...) collects adapters from IAnimal.__subclasses__()
        IAnimal._pi._adapter_cache[Hawk] = None
        interface.clear_adapter_caches(IDog)
        self.assertNotIn(Hawk, IAnimal._pi._adapter_cache)

    def test_parent_interface_finds_adapter_registered_on_child(self):
        adapted = IAnimal.adapt(Hawk(), interface_only=False)
        self.assertIsInstance(adapted, HawkToIDog)

    def test_parent_caches_adapter_found_via_child(self):
        IAnimal.adapt(Hawk(), interface_only=False)
        self.assertIn(Hawk, IAnimal._pi._adapter_cache)
        self.assertIs(IAnimal._pi._adapter_cache[Hawk], HawkToIDog)

    def test_register_type_clears_cache(self):
        IAnimal._pi._adapter_cache[Iguana] = None
        IAnimal.register(Iguana)
        self.assertNotIn(Iguana, IAnimal._pi._adapter_cache)

    def test_register_adapter_only_evicts_from_type_entry(self):
        # Pre-populate cache with an unrelated entry
        IAnimal._pi._adapter_cache[Fish] = None
        # Register a new adapter for Iguana
        register_adapter(lambda obj: CatToIAnimal(obj), Iguana, IAnimal)
        # The Iguana entry should be gone (evicted)
        self.assertNotIn(Iguana, IAnimal._pi._adapter_cache)
        # The Fish entry should be untouched
        self.assertIn(Fish, IAnimal._pi._adapter_cache)
        self.assertIsNone(IAnimal._pi._adapter_cache[Fish])

    def test_stale_none_on_parent_cleared_when_adapter_registered_on_child(self):
        # Fresh types so no adapters are pre-registered
        class IVehicle(Interface):
            def drive(self): pass

        class ICar(IVehicle, Interface):
            def park(self): pass

        class Bicycle:
            pass

        class BicycleToICar(ICar):
            def __init__(self, obj): pass
            def drive(self): pass
            def park(self): pass

        # Prime a stale None on both parent and child: no adapter for Bicycle yet
        self.assertIsNone(IVehicle.adapt_or_none(Bicycle(), interface_only=False))
        self.assertIsNone(ICar.adapt_or_none(Bicycle(), interface_only=False))
        self.assertIsNone(IVehicle._pi._adapter_cache[Bicycle])
        self.assertIsNone(ICar._pi._adapter_cache[Bicycle])

        # Registering on the child must evict the stale entry from both caches
        register_adapter(BicycleToICar, Bicycle, ICar)
        self.assertNotIn(Bicycle, IVehicle._pi._adapter_cache)
        self.assertNotIn(Bicycle, ICar._pi._adapter_cache)

        # Parent can now adapt Bicycle via the child's adapter
        adapted = IVehicle.adapt(Bicycle(), interface_only=False)
        self.assertIsInstance(adapted, BicycleToICar)
