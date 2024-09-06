import dataclasses

import pure_interface


class AnInterface(pure_interface.Interface):
    foo: int
    bar: str


@dataclasses.dataclass
class AnImplementation(AnInterface):
    pass


x = AnImplementation(foo=4, bar="hello")

assert x.foo == 4
assert x.bar == "hello"
