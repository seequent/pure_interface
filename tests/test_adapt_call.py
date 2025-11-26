# --------------------------------------------------------------------------------------------
#  Copyright (c) 2025 Bentley Systems, Incorporated. All rights reserved.
# --------------------------------------------------------------------------------------------

# This tests issue #114

import unittest

from pure_interface import Interface


class IGreetingFactory(Interface):
    style: str

    def __call__(self, name: str) -> str: ...


class FriendlyGreetingFactory(IGreetingFactory):
    style = "friendly"

    def __call__(self, name: str) -> str:
        return f"Hello, {name}! Nice to meet you."


class FormalGreetingFactory(IGreetingFactory):
    style = "formal"

    def __call__(self, name: str) -> str:
        return f"Good day, {name}. It is a pleasure to make your acquaintance."


class InformalGreetingFactory(IGreetingFactory):
    style = "informal"

    def __call__(self, name: str) -> str:
        return f"Hey {name}! What's up?"


class TestAdaptCall(unittest.TestCase):
    def test_adapt_call(self):
        factories = [
            FriendlyGreetingFactory(),
            FormalGreetingFactory(),
            InformalGreetingFactory(),
        ]
        for factory in factories:
            adapted = IGreetingFactory.adapt(factory, interface_only=True)
            self.assertEqual(adapted('World'), factory('World'))
