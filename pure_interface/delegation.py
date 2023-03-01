from __future__ import division, absolute_import, print_function

import operator

from .errors import InterfaceError
from .interface import get_interface_names, type_is_interface, get_type_interfaces, InterfaceType

_composed_types_map = {}
_letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'


class _Delegated:
    def __init__(self, dotted_name):
        self._getter = operator.attrgetter(dotted_name)
        self._impl_name, self._attr_name = dotted_name.rsplit('.', 1)

    def __get__(self, obj, cls):
        if obj is None:
            return self
        return self._getter(obj)

    def __set__(self, obj, value):
        impl = operator.attrgetter(self._impl_name)(obj)
        setattr(impl, self._attr_name, value)


class Delegate:
    """ Mapping based delegate class

    The class attribute pi_attr_delegates is a mapping of implmentation-name -> attr-name-list where
    implementation-name is the name of the attribute containing the implementation.
    The same when an attribute in attr-name-list is accessed on the delegate, the attribute is looked up on
    the implementation.

    e.g. Given
        class MyDelegate(Delegate):
            pi_attr_delegates = {'impl': ['foo', 'bar']}

            def __init__(self, impl):
                self.impl = impl

        d = MyDelegate(impl)
    then
        d.foo will access d.impl.foo
        d.bar('baz') will call d.impl.bar('baz')

    The class attribute pi_attr_delegates values can also contain an interface instead of a list of names.
    For example this is equivalent to the above

        class IFoo(Interface):
            foo: str
            def bar(self, baz):
                pass

        class MyDelegate(Delegate, IFoo):
            pi_attr_delegates = {'impl': IFoo}
            ...


    This is helpful when the attribute names match.
    When they don't, you can use the pi_attr_mapping class atttribute.

    pi_attr_mapping is a mapping of attr -> dotted-name where dotted-name is looked up on self when attr is accessed.

    e.g. The following is equivalent to the example above
        pi_attr_mapping = {'foo': 'impl.foo',
                        'bar': 'impl.bar'}


    pi_attr_fallback is treated a delegate for all attributes defined by base interfaces of the class
    if there is no delegate, mapping or implementation for that attribute.
    This saves repeating IFoo as it is typically a base class also.

        class MyDelegate(Delegate, IFoo):
            pi_attr_fallback = 'impl'

            def __init__(self, impl):
                self.impl = impl

    It is an error to specify the same attribute as a key in pi_attr_mapping and an attr-name in a delegate
    It is an error to specify a delegate name in pi_attr_map.
    If the same attr appears in two delegate lists, then the first one takes precendence

    Note that in methods and properties defined on the delegate class itself take precedence
    (as one would expect).

        class MyDelegate(Delegate, IFoo):
            pi_attr_delegates = {'impl': IFoo}

            def __init__(self, impl):
                self.impl = impl

            @property
            def foo(self):
                return self.impl.foo * 2

            def bar(self, baz):
                return 'my bar'

    However, attempting to set an instance attribute as an override will just set the property on the underlying
    delegate.
    """
    pi_attr_fallback = None
    pi_attr_delegates = {}
    pi_attr_mapping = {}

    def __init_subclass__(cls, **kwargs):
        for delegate, attr_list in cls.pi_attr_delegates.items():
            if isinstance(attr_list, type):
                attr_list = list(get_interface_names(attr_list))
            if delegate in cls.pi_attr_mapping:
                raise ValueError(f'Delegate {delegate} is in pi_attr_map')
            for attr in attr_list:
                if attr in cls.pi_attr_mapping:
                    raise ValueError(f'{attr} in pi_attr_map and handled by delegate {delegate}')
                if attr in cls.__dict__:
                    continue
                dotted_name = f'{delegate}.{attr}'
                setattr(cls, attr, _Delegated(dotted_name))
        for attr, dotted_name in cls.pi_attr_mapping.items():
            if attr not in cls.__dict__:
                setattr(cls, attr, _Delegated(dotted_name))
        if cls.pi_attr_fallback:
            fallback = cls.pi_attr_fallback
            for interface in get_type_interfaces(cls):
                interface_names = get_interface_names(interface)
                for attr in interface_names:
                    if attr not in cls.__dict__:
                        dotted_name = f'{fallback}.{attr}'
                        setattr(cls, attr, _Delegated(dotted_name))

    @classmethod
    def provided_by(cls, obj):
        if not hasattr(cls, 'pi_composed_interfaces'):
            raise InterfaceError('provided_by() can only be called on composed types')
        if isinstance(obj, cls):
            return True
        other_mro = [c for c in type(obj).mro() if type_is_interface(c)]
        my_mro = [c for c in cls.mro() if type_is_interface(c)]
        if set(my_mro) <= set(other_mro):
            return True
        return False


def __composed_init__(self, *args):
    for i, impl in enumerate(args):
        attr = '_' + _letters[i]
        if not isinstance(impl, type(self).pi_composed_interfaces[i]):
            raise ValueError(f'Expected {type(self).pi_composed_interfaces[i]} got {type(impl)} instead')
        setattr(self, attr, impl)


def composed_type(*interfaces: InterfaceType) -> type:
    """Returns a new class which implements all the passed interfaces.
    If the interfaces have duplicate attribute or method names, the first enountered implementation is used.
    Instances of the returned type are passed implementations of the given interfaces in the same order.
    e.g.
    class IA(Interface):
        foo: int
    class IB(Interface):
        bar: int

    class A(IA, object):
        foo = 4
    class B(IB, object):
        bar = 1

    T = composed_type(IA, IB)
    a = A()
    b = B()
    t = T(a, b)
    t.foo -> 4
    t.bar -> 1
    """
    if len(interfaces) < 2:
        raise ValueError('2 or more interfaces required')
    if len(interfaces) > len(_letters):
        raise ValueError(f'Too many interfaces.  Use {len(_letters)} or fewer.')
    interfaces = tuple(interfaces)
    c_type = _composed_types_map.get(interfaces)
    if c_type is not None:
        return c_type
    delegates = {}
    all_names = set()
    for i, interface in enumerate(interfaces):
        if not type_is_interface(interface):
            raise ValueError('all arguments to composed_type must be Interface classes')
        attr = '_' + _letters[i]
        int_names = get_interface_names(interface)
        delegates[attr] = [name for name in int_names if name not in all_names]
        all_names.update(int_names)

    name = ''.join((cls.__name__ for cls in interfaces))
    arg_names = ', '.join((cls.__name__.lower() for cls in interfaces))
    bases = (Delegate,) + interfaces
    cls_attrs = {'__init__': __composed_init__,
                 '__doc__': f'{name}({arg_names})',
                 'pi_attr_delegates': delegates,
                 'pi_composed_interfaces': interfaces,
                 }
    c_type = type(name, bases, cls_attrs)
    _composed_types_map[interfaces] = c_type
    return c_type
