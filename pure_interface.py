try:
    from abc import abstractmethod, abstractproperty, abstractclassmethod, abstractstaticmethod
except ImportError:
    from abc import abstractmethod, abstractproperty


    class abstractclassmethod(classmethod):
        __isabstractmethod__ = True

        def __init__(self, callable):
            callable.__isabstractmethod__ = True
            super(abstractclassmethod, self).__init__(callable)


    class abstractstaticmethod(staticmethod):
        __isabstractmethod__ = True

        def __init__(self, callable):
            callable.__isabstractmethod__ = True
            super(abstractstaticmethod, self).__init__(callable)

import abc
import dis
import types
import sys
import weakref

import six

# OPTIONS
ONLY_FUNCTIONS_AND_PROPERTIES = False  # disallow everything except functions and properties
CHECK_METHOD_SIGNATURES = not hasattr(sys, 'frozen')  # ensure overridden methods have compatible signature


class InterfaceError(Exception):
    pass


class AttributeProperty(property):
    def __init__(self, name):
        self.name = name
        super(AttributeProperty, self).__init__()

    def __get__(self, instance, owner):
        if instance is None:
            return self
        try:
            return instance.__dict__[self.name]
        except KeyError:
            raise AttributeError(self.name)

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

    def __delete__(self, instance):
        try:
            del instance.__dict__[self.name]
        except KeyError:
            raise AttributeError(self.name)


def _builtin_attrs(name):
    return name in ('__doc__', '__module__', '__qualname__', '__abstractmethods__', '__dict__',
                    '_abc_cache', '_abc_registry')


def _type_is_pure_interface(cls):
    """ Return True if cls is a pure interface"""
    if cls is object:
        return False
    if hasattr(cls, '_pi_type_is_pure_interface'):
        return cls._pi_type_is_pure_interface
    if issubclass(type(cls), abc.ABCMeta):
        for attr, value in six.iteritems(cls.__dict__):
            if _builtin_attrs(attr):
                continue
            if callable(value):
                if not _is_empty_function(value):
                    return False
            elif isinstance(value, property):
                for func in (value.fget, value.fset, value.fdel):
                    if func is not None and not _is_empty_function(func):
                        return False
        return True

    return False


def _is_empty_function(func):
    if isinstance(func, (staticmethod, classmethod, types.MethodType)):
        func = six.get_method_function(func)
    if isinstance(func, property):
        func = property.fget
    if six.PY2:
        code_obj = six.get_function_code(func)
        # quick check
        if code_obj.co_code == b'd\x00\x00S' and code_obj.co_consts[0] is None:
            return True
        if code_obj.co_code == b'd\x01\x00S' and code_obj.co_consts[1] is None:
            return True
        # convert bytes to instructions
        instructions = []
        instruction = None
        for byte in code_obj.co_code:
            byte = ord(byte)
            if instruction is None:
                instruction = [byte]
            else:
                instruction.append(byte)
            if instruction[0] < dis.HAVE_ARGUMENT or len(instruction) == 3:
                instruction[0] = dis.opname[instruction[0]]
                instructions.append(tuple(instruction))
                instruction = None
        if len(instructions) < 2:
            return True  # this never happens as there is always the implicit return None which is 2 instructions
        assert instructions[-1] == ('RETURN_VALUE',)  # returns TOS (top of stack)
        instruction = instructions[-2]
        if not (instruction[0] == 'LOAD_CONST' and code_obj.co_consts[instruction[1]] is None):  # TOS is None
            return False
        instructions = instructions[:-2]
        if len(instructions) == 0:
            return True
        # look for raise NotImplementedError
        if instructions[-1] == ('RAISE_VARARGS', 1, 0):
            # the thing we are raising should be the result of __call__  (instantiating exception object)
            if instructions[-2][0] == 'CALL_FUNCTION':
                for instr in instructions[:-2]:
                    if instr[0] == 'LOAD_GLOBAL' and code_obj.co_names[instr[1]] == 'NotImplementedError':
                        return True
    else:  # python 3
        instructions = list(dis.Bytecode(func))
        if len(instructions) < 2:
            return True  # this never happens as there is always the implicit return None which is 2 instructions
        last_instruction = instructions[-1]
        if not (last_instruction.opname == 'RETURN_VALUE' and last_instruction.arg is None):
            # not return None
            return False
        instructions = instructions[:-1]
        last_instruction = instructions[-1]
        if last_instruction.opname == 'LOAD_CONST' and last_instruction.argval is None:
            instructions = instructions[:-1]  # this is what we expect, consume
        if len(instructions) == 0:
            return True  # empty
        last_instruction = instructions[-1]
        if last_instruction.opname == 'RAISE_VARARGS':
            if len(instructions) < 3:
                return False
            # the thing we are raising should be the result of __call__  (instantiating exception object)
            if instructions[-2].opname == 'CALL_FUNCTION':
                for instr in instructions[:-2]:
                    if instr.opname == 'LOAD_GLOBAL' and instr.argval == 'NotImplementedError':
                        return True

    return False


def _get_function_signature(function):
    code_obj = function.__code__
    args = code_obj.co_varnames[:code_obj.co_argcount]
    return args, len(function.__defaults__) if function.__defaults__ is not None else 0


def _signatures_are_consistent(func_sig, base_sig):
    # TODO: allow new arguments in func_sig if they have default values
    func_args, func_num_defaults = func_sig
    base_args, base_num_defaults = base_sig
    base_num_args = len(base_args)
    func_num_args = len(func_args)
    func_num_required = func_num_args - func_num_defaults
    base_num_required = base_num_args - base_num_defaults
    return (func_args[:base_num_args] == base_args and  # parameter names match
            func_num_args - base_num_args <= func_num_defaults and  # new args have defaults
            func_num_required <= base_num_required  # number of required args does not increase
            )


def _method_signatures_match(name, func, bases):
    func_sig = _get_function_signature(func)
    for base in bases:
        if base is object:
            continue
        if hasattr(base, name):
            base_func = getattr(base, name)
            if hasattr(base_func, six._meth_func):
                base_func = six.get_method_function(base_func)
            base_sig = _get_function_signature(base_func)
            return _signatures_are_consistent(func_sig, base_sig)
    return True


class PureInterfaceType(abc.ABCMeta):
    def __new__(mcs, clsname, bases, attributes):
        type_is_interface = all(_type_is_pure_interface(cls) for cls in bases)
        if clsname == 'PureInterface' and attributes['__module__'] == 'pure_interface':
            type_is_interface = True
        else:
            if bases[0] is object:
                bases = bases[1:]  # create a consistent MRO order
        interface_method_names = set()
        interface_property_names = set()
        for base in bases:
            base_interface_method_names = getattr(base, '_pi_interface_method_names', set())
            interface_method_names.update(base_interface_method_names)
            base_interface_property_names = getattr(base, '_pi_interface_property_names', set())
            interface_property_names.update(base_interface_property_names)
        if type_is_interface:
            # all methods and properties are abstract
            namespace = {}
            functions = []
            for name, value in six.iteritems(attributes):
                if _builtin_attrs(name):
                    pass
                elif getattr(value, '__isabstractmethod__', False):
                    if isinstance(value, (staticmethod, classmethod, types.FunctionType)):
                        interface_method_names.add(name)
                    elif isinstance(value, property):
                        interface_property_names.add(name)
                elif isinstance(value, staticmethod):
                    func = six.get_method_function(value)
                    functions.append(func)
                    value = abstractstaticmethod(func)
                    interface_method_names.add(name)
                elif isinstance(value, classmethod):
                    func = six.get_method_function(value)
                    functions.append(func)
                    value = abstractclassmethod(func)
                    interface_method_names.add(name)
                elif isinstance(value, types.FunctionType):
                    functions.append(value)
                    value = abstractmethod(value)
                    interface_method_names.add(name)
                elif isinstance(value, property):
                    interface_property_names.add(name)
                    functions.extend([value.fget, value.fset, value.fdel])  # may contain Nones
                    value = abstractproperty(value.fget, value.fset, value.fdel)
                elif ONLY_FUNCTIONS_AND_PROPERTIES:
                    raise InterfaceError('ONLY_FUNCTIONS_AND_PROPERTIES option voilated by {}'.format(value))
                namespace[name] = value
            for func in functions:
                if func is not None and not _is_empty_function(func):
                    raise InterfaceError('Function "{}" is not empty'.format(func.__name__))
        else:  # concrete sub-type
            namespace = attributes
        if CHECK_METHOD_SIGNATURES:
            for name in interface_method_names:
                if name not in attributes:
                    continue
                value = attributes[name]
                if not isinstance(value, (staticmethod, classmethod, types.FunctionType)):
                    raise InterfaceError('Interface method over-ridden with non-method')
                if isinstance(value, (staticmethod, classmethod)):
                    func = six.get_method_function(value)
                else:
                    func = value
                if not _method_signatures_match(name, func, bases):
                    msg = '{module}.{clsname}.{name} argments does not match base class'.format(
                        module=attributes['__module__'], clsname=clsname, name=name)
                    raise InterfaceError(msg)

        cls = abc.ABCMeta.__new__(mcs, clsname, bases, namespace)
        cls._pi_type_is_pure_interface = type_is_interface
        cls._pi_abstractproperties = frozenset()
        cls._pi_interface_method_names = frozenset(interface_method_names)
        cls._pi_interface_property_names = frozenset(interface_property_names)
        cls._pi_adapters = weakref.WeakKeyDictionary()
        if not type_is_interface:
            abstract_properties = set()
            functions = []
            for attr in cls.__abstractmethods__:
                value = getattr(cls, attr)
                if isinstance(value, abstractproperty):
                    functions.extend([value.fget, value.fset, value.fdel])  # may contain Nones
                    setattr(cls, attr, AttributeProperty(attr))
                    abstract_properties.add(attr)
            cls._pi_abstractproperties = frozenset(abstract_properties)
            abstractmethods = set(cls.__abstractmethods__) - abstract_properties
            for func in functions:
                if func is not None and func.__name__ in abstractmethods:
                    abstractmethods.discard(func.__name__)
            cls.__abstractmethods__ = frozenset(abstractmethods)
        if type_is_interface and not cls.__abstractmethods__:
            cls.__abstractmethods__ = frozenset({''})  # empty interfaces still should not be instantiated
        return cls

    def __call__(cls, *args, **kwargs):
        self = abc.ABCMeta.__call__(cls, *args, **kwargs)
        for attr in cls._pi_abstractproperties:
            if not hasattr(self, attr):
                raise TypeError('__init__ does not create required attribute "{}"'.format(attr))
        return self

    def __instancecheck__(cls, instance):
        if super(PureInterfaceType, cls).__instancecheck__(instance):
            return True
        if not cls._pi_type_is_pure_interface:
            return False  # can't do duck type checking for sub-classes of concrete types
        # duck-type checking
        subclass = type(instance)
        for attr in cls._pi_interface_method_names:
            subtype_value = getattr(subclass, attr, None)
            if not callable(subtype_value):
                return False
        for attr in cls._pi_interface_property_names:
            if not hasattr(instance, attr):
                return False
        return True

    def __subclasscheck__(cls, subclass):
        if super(PureInterfaceType, cls).__subclasscheck__(subclass):
            return True
        if not cls._pi_type_is_pure_interface:
            return False  # can't do duck type checking for sub-classes of concrete types
        # duck-type checking
        for attr in cls._pi_interface_method_names:
            subtype_value = getattr(subclass, attr, None)
            if not callable(subtype_value):
                return False
        for attr in cls._pi_interface_property_names:
            if not hasattr(subclass, attr):
                return False

        cls._abc_registry.add(subclass)
        abc.ABCMeta._abc_invalidation_counter += 1  # Invalidate negative cache
        return True


@six.add_metaclass(PureInterfaceType)
class PureInterface(abc.ABC if hasattr(abc, 'ABC') else object):
    pass


# adaption
def adapts(from_type, to_interface):
    """Class decorator for declaring an adapter.
    """

    def decorator(cls):
        register_adapter(cls, from_type, to_interface)
        return cls

    return decorator


def register_adapter(adapter, from_type, to_interface):
    # types: (from_type) -> to_interface, type, PureInterfaceType
    if not callable(adapter):
        raise ValueError('adapter must be callable')
    if not isinstance(from_type, type):
        raise ValueError('{} must be a type'.format(from_type))
    if isinstance(None, from_type):
        raise ValueError('Cannot adapt None type')
    if not (isinstance(to_interface, type) and getattr(to_interface, '_pi_type_is_pure_interface', False)):
        raise ValueError('{} is not an interface'.format(to_interface))
    if from_type in to_interface._pi_adapters:
        raise ValueError('{} already has an adapter to {}'.format(from_type, to_interface))
    to_interface._pi_adapters[from_type] = weakref.proxy(adapter)


def adapt_to_interface(obj, to_interface):
    """ Adapts obj to interface, returning obj if isinstance(obj, to_interface) is True
    and raising ValueError if no adapter is found
    """
    if isinstance(obj, to_interface):
        return obj
    adapters = getattr(to_interface, '_pi_adapters', {})
    if not adapters:
        raise ValueError('Cannot adapt {} to {}'.format(obj, to_interface))
    for obj_class in type(obj).__mro__:
        if obj_class in adapters:
            factory = adapters[obj_class]
            adapted = factory(obj)
            if not isinstance(adapted, to_interface):
                raise ValueError('Adapter {} does not implement interface {}'.format(factory, to_interface))
            return adapted
    raise ValueError('Cannot adapt {} to {}'.format(obj, to_interface))


def adapt_to_interface_or_none(obj, to_interface):
    """ Adapt obj to to_interface or return None if adaption fails"""
    try:
        return adapt_to_interface(obj, to_interface)
    except ValueError:
        return None


def iter_adapted(objects, to_interface):
    """ Generates adaptions of given objects to this interface.
    Objects that cannot be adapted to this interface are silently skipped.
    """

    for obj in objects:
        f = adapt_to_interface_or_none(obj, to_interface)
        if f is not None:
            yield f
