from functools import singledispatchmethod
from typing import Any
import unittest

import pure_interface


class TestSingleDispatch(unittest.TestCase):
    def test_single_dispatch_allowed(self):
        class IPerson(pure_interface.Interface):
            @singledispatchmethod
            def greet(self, other_person: Any) -> str:
                pass

        self.assertSetEqual(pure_interface.get_interface_method_names(IPerson), {'greet'})

    def test_single_dispatch_checked(self):
        class IPerson(pure_interface.Interface):
            def greet(self) -> str:
                pass

        pure_interface.set_is_development(True)
        with self.assertRaises(pure_interface.InterfaceError):
            class Person(IPerson):
                @singledispatchmethod
                def greet(self, other_person: Any) -> str:
                    pass

