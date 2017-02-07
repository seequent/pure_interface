
try:
    from abc import abstractmethod, abstractproperty, abstractclassmethod, abstractstaticmethod
except NameError:
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

import six

# OPTIONS
ONLY_FUNCTIONS_AND_PROPERTIES = False  # disallow everything except functions and properties


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
    if cls is object:
        return False
    if hasattr(cls, '_type_is_pure_interface'):
        return cls._type_is_pure_interface
    if issubclass(type(cls), abc.ABCMeta):
        for attr, value in six.iteritems(cls.__dict__):
            if _builtin_attrs(attr):
                continue
            if callable(value):
                if not _is_empty_function(value):
                    return False
            elif isinstance(value, property):
                for func in (value.fget, value.fset, value.fdel):
                    if not _is_empty_function(func):
                        return False
        return True

    return False


def _is_empty_function(func):
    if isinstance(func, (staticmethod, classmethod, types.MethodType)):
        func = six.get_method_function(func)
    if isinstance(func, property):
        func = property.fget
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


class PureInterfaceType(abc.ABCMeta):
    def __new__(mcs, clsname, bases, attributes):
        type_is_interface = all(_type_is_pure_interface(cls) for cls in bases)
        if clsname == 'PureInterface' and attributes['__module__'] == 'pure_interface':
            type_is_interface = True
        else:
            if bases[0] is object:
                bases = bases[1:]  # create a consistent MRO order
        if type_is_interface:
            # all methods and properties are abstract
            namespace = {}
            functions = []
            for name, value in six.iteritems(attributes):
                if _builtin_attrs(name):
                    pass
                elif isinstance(value, staticmethod):
                    func = six.get_method_function(value)
                    functions.append(func)
                    value = abstractstaticmethod(func)
                elif isinstance(value, classmethod):
                    func = six.get_method_function(value)
                    functions.append(func)
                    value = abstractclassmethod(func)
                elif isinstance(value, types.FunctionType):
                    functions.append(value)
                    value = abstractmethod(value)
                elif isinstance(value, property):
                    functions.extend([value.fget, value.fset, value.fdel])  # may contain Nones
                    value = abstractproperty(value.fget, value.fset, value.fdel)
                elif ONLY_FUNCTIONS_AND_PROPERTIES:
                    raise InterfaceError('ONLY_FUNCTIONS_AND_PROPERTIES option voilated by {}'.format(value))
                namespace[name] = value
            for func in functions:
                if func is not None and not _is_empty_function(func):
                    raise InterfaceError('Function "{}" is not empty'.format(func.__name__))
        else:
            namespace = attributes
        cls = abc.ABCMeta.__new__(mcs, clsname, bases, namespace)
        cls._type_is_pure_interface = type_is_interface
        cls.__abstractproperties = frozenset()
        if not type_is_interface:
            abstract_properties = set()
            functions = []
            for attr in cls.__abstractmethods__:
                value = getattr(cls, attr)
                if isinstance(value, abstractproperty):
                    functions.extend([value.fget, value.fset, value.fdel])  # may contain Nones
                    setattr(cls, attr, AttributeProperty(attr))
                    abstract_properties.add(attr)
            cls.__abstractproperties = frozenset(abstract_properties)
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
        for attr in cls.__abstractproperties:
            if not hasattr(self, attr):
                raise TypeError('__init__ does not create required attribute "{}"'.format(attr))
        return self


@six.add_metaclass(PureInterfaceType)
class PureInterface(object):
    pass
