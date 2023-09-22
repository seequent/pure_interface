import pure_interface
import dataclasses

class IX(pure_interface.Interface):
    foo: int
    bar: str

@dataclasses.dataclass
class X(IX):
    pass

x = X(foo=4, bar='hello')

