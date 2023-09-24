""" decorator function for sub-interfaces

A sub-interface is a non-empty subset of another, larger, interface.
The decorator checks that the sub-interface is infact a subset and
registers the larger interface as an implementation of the sub-interface.
"""
from inspect import signature
from typing import Callable, TypeVar, Type
from . import errors, interface

AnotherInterfaceType = TypeVar('AnotherInterfaceType', bound=Type[interface.Interface])


def _check_interfaces_match(large_interface, small_interface):
    large_attributes = interface.get_interface_attribute_names(large_interface)
    small_attributes = interface.get_interface_attribute_names(small_interface)
    large_methods = interface.get_interface_method_names(large_interface)
    small_methods = interface.get_interface_method_names(small_interface)

    if len(small_attributes) + len(small_methods) == 0:
        raise interface.InterfaceError(f'Sub-interface {small_interface.__name__} is empty')

    if not small_attributes.issubset(large_attributes):
        new_attrs = sorted(small_attributes.difference(large_attributes))
        attr_str = ', '.join(new_attrs)
        msg = f'{small_interface.__name__} has attributes that are not on {large_interface.__name__}: {attr_str}'
        raise interface.InterfaceError(msg)

    if not small_methods.issubset(large_methods):
        new_methods = sorted(small_methods.difference(large_methods))
        method_str = ', '.join(new_methods)
        msg = f'{small_interface.__name__} has methods that are not on {large_interface.__name__}: {method_str}'
        raise interface.InterfaceError(msg)

    for method_name in small_methods:
        large_method = getattr(large_interface, method_name)
        small_method = getattr(small_interface, method_name)
        if signature(large_method) != signature(small_method):
            msg = (f'Signature of method {method_name} on {large_interface.__name__} '
                   f'and {small_interface.__name__} must match exactly')
            raise interface.InterfaceError(msg)


def sub_interface_of(
    large_interface: interface.AnInterfaceType
) -> Callable[[AnotherInterfaceType], AnotherInterfaceType]:
    if not interface.type_is_interface(large_interface):
        raise errors.InterfaceError(f'sub_interface_of argument {large_interface} is not an interface type')

    def decorator(small_interface: AnotherInterfaceType) -> AnotherInterfaceType:
        if not interface.type_is_interface(small_interface):
            raise errors.InterfaceError('class decorated by sub_interface_of must be an interface type')
        _check_interfaces_match(large_interface, small_interface)
        small_interface.register(large_interface)  # type: ignore[arg-type]

        return small_interface

    return decorator
