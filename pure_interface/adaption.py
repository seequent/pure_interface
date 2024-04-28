from __future__ import division, absolute_import, print_function

import functools
import inspect
import types
from typing import Any, Type, TypeVar, Callable, Optional, Union
import typing
import warnings

from .errors import InterfaceError, AdaptionError
from .interface import AnInterface, Interface, InterfaceType, type_is_interface
from .interface import get_type_interfaces, get_pi_attribute


def adapts(from_type: Any, to_interface: Optional[Type[Interface]] = None) -> Callable[[Any], Any]:
    """Class or function decorator for declaring an adapter from a type to an interface.
    E.g.
        @adapts(MyClass, MyInterface)
        def interface_factory(obj):
            ....

    If decorating a class to_interface may be None to use the first interface in the class's MRO.
    E.g.
        @adapts(MyClass)
        class MyClassToInterfaceAdapter(MyInterface):
            def __init__(self, obj):
                ....
            ....
        will adapt MyClass to MyInterface using MyClassToInterfaceAdapter
    """

    def decorator(cls):
        if to_interface is None:
            interfaces = get_type_interfaces(cls)
            if interfaces:
                interface = interfaces[0]
            elif isinstance(cls, type):
                raise InterfaceError('Class {} does not provide any interfaces'.format(cls.__name__))
            else:
                raise InterfaceError('to_interface must be specified when decorating non-classes')
        else:
            interface = to_interface
        register_adapter(cls, from_type, interface)
        return cls

    return decorator


T = TypeVar('T')
U = TypeVar('U')  # U can be a structural type so can't expect it to be a subclass of Interface


def register_adapter(
        adapter: Union[Callable[[T], U], Type[U]],
        from_type: Type[T],
        to_interface: Type[Interface]) -> None:
    """ Registers adapter to convert instances of from_type to objects that provide to_interface
    for the to_interface.adapt() method.

    :param adapter: callable that takes an instance of from_type and returns an object providing to_interface.
    :param from_type: a type to adapt from
    :param to_interface: an Interface class to adapt to.
    """
    if not callable(adapter):
        raise AdaptionError('adapter must be callable')
    if not isinstance(from_type, type):
        raise AdaptionError('{} must be a type'.format(from_type))
    if not (isinstance(to_interface, type) and get_pi_attribute(to_interface, 'type_is_interface', False)):
        raise AdaptionError('{} is not an interface'.format(to_interface))
    adapters = get_pi_attribute(to_interface, 'adapters')
    if from_type in adapters:
        raise AdaptionError('{} already has an adapter to {}'.format(from_type, to_interface))

    adapters[from_type] = adapter


class AdapterTracker(object):
    """ The idiom of checking if `x is b` is broken for adapted objects because a new adapter is potentially
    instantiated each time x or b is adapted.  Also in some context we adapt the same objects many times and don't
    want the overhead of lots of copies.  This class provides adapt() and adapt_or_none() methods that track adaptions.
    Thus if `x is b` is `True` then `adapter.adapt(x, I) is adapter.adapt(b, I)` is `True`.
    """
    def __init__(self, mapping_factory=dict):
        self._factory = mapping_factory
        self._adapters = mapping_factory()

    def adapt(self, obj: Any, interface: Type[AnInterface]) -> AnInterface:
        """ Adapts `obj` to `interface`"""
        try:
            return self._adapters[interface][obj]
        except KeyError:
            return self._adapt(obj, interface)

    def adapt_or_none(self, obj: Any, interface: Type[AnInterface]) -> Optional[AnInterface]:
        """ Adapt obj to interface returning None on failure."""
        try:
            return self.adapt(obj, interface)
        except ValueError:
            return None

    def clear(self) -> None:
        """ Clears the cached adapters."""
        self._adapters = self._factory()

    def _adapt(self, obj: Any, interface: Type[AnInterface]) -> AnInterface:
        adapted = interface.adapt(obj)
        try:
            adapters = self._adapters[interface]
        except KeyError:
            adapters = self._adapters[interface] = self._factory()
        adapters[obj] = adapted
        return adapted


def _interface_from_anno(annotation: Any) -> Optional[InterfaceType]:
    """ Typically the annotation is the interface,  but if a default value of None is given the annotation is
    a Union[interface, None] a.k.a. Optional[interface]. Lets be nice and support those too.
    """
    try:
        if issubclass(annotation, Interface):
            return annotation
    except TypeError:
        pass
    if hasattr(annotation, '__origin__') and hasattr(annotation, '__args__'):
        # could be a Union
        if annotation.__origin__ is not Union:
            return None
        for arg_type in annotation.__args__:
            if type_is_interface(arg_type):
                return arg_type

    return None


def adapt_args(*func_arg, **kwarg_types):
    """ adapts arguments to the decorated function to the types given.  For example:

            @adapt_args(foo=IFoo, bar=IBar)
            def my_func(foo, bar):
                pass

        This would adapt the foo parameter to IFoo (with IFoo.optional_adapt(foo)) and bar to IBar (using IBar.adapt(bar))
        before passing them to my_func.  `None` values are never adapted, so my_func(foo, None) will work, otherwise
        AdaptionError is raised if the parameter is not adaptable.
        All arguments must be specified as keyword arguments

            @adapt_args(IFoo, IBar)   # NOT ALLOWED
            def other_func(foo, bar):
                pass

        Parameters are only adapted if not None.  This is useful for optional args:

            @adapt_args(foo=IFoo)
            def optional_func(foo=None):
                pass

        In Python 3 the types can be taken from the annotations.  Optional[interface] is supported too.

            @adapt_args
            def my_func(foo: IFoo, bar: Optional[IBar] = None):
                pass

    """
    def decorator(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            adapted_kwargs = inspect.getcallargs(func, *args, **kwargs)
            for name, interface in kwarg_types.items():
                kwarg = adapted_kwargs.get(name, None)
                adapted_kwargs[name] = InterfaceType.optional_adapt(interface, kwarg)

            return func(**adapted_kwargs)
        return wrapped

    if func_arg:
        if len(func_arg) != 1:
            raise AdaptionError('Only one posititional argument permitted')
        if not isinstance(func_arg[0], types.FunctionType):
            raise AdaptionError('Positional argument must be a function (to decorate)')
        if kwarg_types:
            raise AdaptionError('keyword parameters not permitted with positional argument')
        funcn = func_arg[0]
        annotations = typing.get_type_hints(funcn)
        if not annotations:
            warnings.warn('No annotations for {}. '
                          'Add annotations or pass explicit argument types to adapt_args'.format(funcn.__name__),
                          stacklevel=2)
        for key, anno in annotations.items():
            i_face = _interface_from_anno(anno)
            if i_face is not None:
                kwarg_types[key] = i_face
        return decorator(funcn)

    for key, i_face in kwarg_types.items():
        i_face = typing.cast(InterfaceType, i_face)  # keep mypy happy
        can_adapt = type_is_interface(i_face)
        if not can_adapt:
            raise AdaptionError('adapt_args parameter values must be subtypes of Interface')
    return decorator
