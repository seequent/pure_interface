
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
    code_obj = six.get_function_code(function)
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
        for base in bases:
            base_interface_method_names = getattr(base, '_interface_method_names', set())
            interface_method_names.update(base_interface_method_names)
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
        cls._type_is_pure_interface = type_is_interface
        cls._abstractproperties = frozenset()
        cls._interface_method_names = frozenset(interface_method_names)
        if not type_is_interface:
            abstract_properties = set()
            functions = []
            for attr in cls.__abstractmethods__:
                value = getattr(cls, attr)
                if isinstance(value, abstractproperty):
                    functions.extend([value.fget, value.fset, value.fdel])  # may contain Nones
                    setattr(cls, attr, AttributeProperty(attr))
                    abstract_properties.add(attr)
            cls._abstractproperties = frozenset(abstract_properties)
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
        for attr in cls._abstractproperties:
            if not hasattr(self, attr):
                raise TypeError('__init__ does not create required attribute "{}"'.format(attr))
        return self

    def __instancecheck__(cls, instance):
        if super(PureInterfaceType, cls).__instancecheck__(instance):
            return True
        # duck-type checking
        subtype = type(instance)
        implemented_by_class = True
        for attr in cls.__abstractmethods__:
            cls_value = getattr(cls, attr)
            subtype_value = getattr(subtype, attr, None)
            if subtype_value is None:
                implemented_by_class = False
                try:
                    subtype_value = getattr(instance, attr)
                except AttributeError:
                    return False
            if callable(cls_value) and not callable(subtype_value):
                return False

        if implemented_by_class:
            cls.register(subtype)
        return True


@six.add_metaclass(PureInterfaceType)
class PureInterface(abc.ABC):
    pass
