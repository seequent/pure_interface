import collections
import sys
import typing

from .interface import get_type_interfaces, get_interface_attribute_names

try:
    import dataclasses


    def _get_interface_annotions(cls):
        annos = collections.OrderedDict()
        for subcls in get_type_interfaces(cls)[::-1]:
            sc_annos = typing.get_type_hints(subcls)
            sc_names = get_interface_attribute_names(subcls)
            for key, value in sc_annos.items():  # sc_annos has the correct ordering
                if key in sc_names:
                    annos[key] = sc_annos[key]
        return annos


    if sys.version_info[:2] < (3, 10):
        def dataclass(_cls=None, init=True, repr=True, eq=True, order=False,
                      unsafe_hash=False, frozen=False):
            """Returns the same class as was passed in, with dunder methods
            added based on the fields defined in the class.

            Examines PEP 526 __annotations__ to determine fields.

            If init is true, an __init__() method is added to the class. If
            repr is true, a __repr__() method is added. If order is true, rich
            comparison dunder methods are added. If unsafe_hash is true, a
            __hash__() method function is added. If frozen is true, fields may
            not be assigned to after instance creation.
            """

            def wrap(cls):
                # dataclasses only operates on annotations in the current class
                # get all interface attributes and add them to this class
                interface_annos = _get_interface_annotions(cls)
                annos = cls.__dict__.get('__annotations__', {})
                interface_annos.update(annos)
                cls.__annotations__ = interface_annos
                return dataclasses._process_class(cls, init, repr, eq, order, unsafe_hash, frozen)

            # See if we're being called as @dataclass or @dataclass().
            if _cls is None:
                # We're called with parens.
                return wrap
            # We're called as @dataclass without parens.
            return wrap(_cls)
    else:

        def dataclass(cls=None, *, init=True, repr=True, eq=True, order=False, unsafe_hash=False,
                      frozen=False, match_args=True, kw_only=False, slots=False):
            """Returns the same class as was passed in, with dunder methods
            added based on the fields defined in the class.

            Examines PEP 526 __annotations__ to determine fields.

            If init is true, an __init__() method is added to the class. If
            repr is true, a __repr__() method is added. If order is true, rich
            comparison dunder methods are added. If unsafe_hash is true, a
            __hash__() method function is added. If frozen is true, fields may
            not be assigned to after instance creation.
            """

            def wrap(cls):
                # dataclasses only operates on annotations in the current class
                # get all interface attributes and add them to this class
                interface_annos = _get_interface_annotions(cls)
                annos = cls.__dict__.get('__annotations__', {})
                interface_annos.update(annos)
                cls.__annotations__ = interface_annos
                return dataclasses._process_class(cls, init, repr, eq, order, unsafe_hash,
                                                  frozen, match_args, kw_only, slots)

            # See if we're being called as @dataclass or @dataclass().
            if cls is None:
                # We're called with parens.
                return wrap
            # We're called as @dataclass without parens.
            return wrap(cls)


except ImportError:
    pass
