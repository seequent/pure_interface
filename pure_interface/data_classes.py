import collections
import dataclasses
import sys
import typing

from .interface import get_type_interfaces, get_interface_attribute_names


_dataclass_defaults = dict(init=True, repr=True, eq=True, order=False,
                           unsafe_hash=False, frozen=False, match_args=True, kw_only=False,
                           slots=False, weakref_slot=False)


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
    _dataclass_args = ('init', 'repr', 'eq', 'order', 'unsafe_hash', 'frozen')
elif sys.version_info[:2] < (3, 11):
    _dataclass_args = ('init', 'repr', 'eq', 'order', 'unsafe_hash', 'frozen',
                       'match_args', 'kw_only', 'slots')
else:
    _dataclass_args = ('init', 'repr', 'eq', 'order', 'unsafe_hash', 'frozen',
                       'match_args', 'kw_only', 'slots', 'weakref_slot')


def dataclass(_cls: typing.Union[type, None] = None, **kwargs):
    """Returns the same class as was passed in, with dunder methods
    added based on the fields defined in the class.
    """
    arg_tuple = tuple(kwargs.get(arg_name, _dataclass_defaults[arg_name]) for arg_name in _dataclass_args)

    def wrap(cls):
        # dataclasses only operates on annotations in the current class
        # get all interface attributes and add them to this class
        interface_annos = _get_interface_annotions(cls)
        annos = cls.__dict__.get('__annotations__', {})
        interface_annos.update(annos)
        cls.__annotations__ = interface_annos
        return dataclasses._process_class(cls, *arg_tuple)

    # See if we're being called as @dataclass or @dataclass().
    if _cls is None:
        # We're called with parens.
        return wrap
    # We're called as @dataclass without parens.
    return wrap(_cls)
