"""
pure_interface enforces empty functions and properties on interfaces and provides adaption and structural type checking.
"""
from __future__ import division, print_function, absolute_import

import abc
from abc import abstractmethod, abstractclassmethod, abstractstaticmethod
import collections
import dis
import functools
import inspect
from inspect import signature, Signature, Parameter
import types
from typing import Any, Callable, List, Optional, Iterable, FrozenSet, Type, TypeVar
import typing
import sys
import warnings
import weakref


__version__ = '5.0.1'


is_development = not hasattr(sys, 'frozen')
missing_method_warnings = []


class PureInterfaceError(Exception):
    """ All exceptions raised by this module are subclasses of this exception """
    pass


class InterfaceError(PureInterfaceError, TypeError):
    """ An error with an interface class definition or implementation"""
    pass


class AdaptionError(PureInterfaceError, ValueError):
    """ An adaption error """
    pass


def no_adaption(obj):
    return obj


PI = TypeVar('PI', bound='Interface')


class _PIAttributes(object):
    """ rather than clutter the class namespace with lots of _pi_XXX attributes, collect them all here"""
    def __init__(self, type_is_interface, abstract_properties, interface_method_signatures, interface_attribute_names):
        self.type_is_interface = type_is_interface
        # abstractproperties are checked for at instantiation.
        # When concrete classes use a @property then they are removed from this set
        self.abstractproperties = frozenset(abstract_properties)
        self.interface_method_names = frozenset(interface_method_signatures.keys())  # type: FrozenSet[str]
        self.interface_attribute_names = frozenset(interface_attribute_names)  # type: FrozenSet[str]
        self.interface_method_signatures = interface_method_signatures
        self.adapters = weakref.WeakKeyDictionary()
        self.structural_subclasses = set()
        self.impl_wrapper_type = None

    @property
    def interface_names(self):
        return self.interface_method_names.union(self.interface_attribute_names)


class _ImplementationWrapper(object):
    def __init__(self, implementation, interface):
        object.__setattr__(self, '_ImplementationWrapper__impl', implementation)
        object.__setattr__(self, '_ImplementationWrapper__interface', interface)
        object.__setattr__(self, '_ImplementationWrapper__interface_attrs', interface._pi.interface_names)
        object.__setattr__(self, '_ImplementationWrapper__interface_name', interface.__name__)

    def __getattr__(self, attr):
        impl = self.__impl
        if attr in self.__interface_attrs:
            return getattr(impl, attr)
        else:
            raise AttributeError("'{}' interface has no attribute '{}'".format(self.__interface_name, attr))

    def __setattr__(self, key, value):
        if key in self.__interface_attrs:
            setattr(self.__impl, key, value)
        else:
            raise AttributeError("'{}' interface has no attribute '{}'".format(self.__interface_name, key))


def _builtin_attrs(name):
    """ These attributes are ignored when checking ABC types for emptyness.
    """
    return name in ('__doc__', '__module__', '__qualname__', '__abstractmethods__', '__dict__',
                    '__metaclass__', '__weakref__', '__subclasshook__',
                    '_abc_cache', '_abc_impl', '_abc_registry', '_abc_negative_cache_version', '_abc_negative_cache',
                    '_pi', '_pi_unwrap_decorators')


def _get_pi_attribute(cls, attr_name, default=None):
    if hasattr(cls, '_pi'):
        return getattr(cls._pi, attr_name)
    else:
        return default


def _type_is_interface(cls):
    """ Return True if cls is a pure interface or an empty ABC class"""
    if cls is object:
        return False
    if hasattr(cls, '_pi'):
        return cls._pi.type_is_interface
    if issubclass(type(cls), abc.ABCMeta):
        for attr, value in cls.__dict__.items():
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


def _get_abc_interface_props_and_funcs(cls):
    properties = set()
    function_sigs = {}
    if not hasattr(cls, '__abstractmethods__'):
        return properties, function_sigs
    for name in cls.__abstractmethods__:
        if _builtin_attrs(name):
            pass  # shortcut
        value = getattr(cls, name)
        if isinstance(value, (staticmethod, classmethod, types.MethodType)):
            func = value.__func__
            function_sigs[name] = signature(func)
        elif isinstance(value, types.FunctionType):
            function_sigs[name] = signature(value)
        elif isinstance(value, property):
            properties.add(name)

    return properties, function_sigs


def _unwrap_function(func):
    """ Look for decorated functions and return the wrapped function.
    """
    while hasattr(func, '__wrapped__'):
        func = func.__wrapped__
    return func


def _is_empty_function(func, unwrap=False):
    """ Return True if func is considered empty.
     All functions with no return statement have an implicit return None - this is explicit in the code object.
    """
    if isinstance(func, (staticmethod, classmethod, types.MethodType)):
        func = func.__func__
    if isinstance(func, property):
        func = property.fget
    if unwrap:
        func = _unwrap_function(func)
    try:
        code_obj = func.__code__
    except AttributeError:
        # This callable is something else - assume it is OK.
        return True

    # quick check
    if code_obj.co_code == b'd\x00\x00S' and code_obj.co_consts[0] is None:
        return True
    if code_obj.co_code == b'd\x01\x00S' and code_obj.co_consts[1] is None:
        return True
    # convert bytes to instructions
    instructions = _get_instructions(code_obj)
    if len(instructions) < 2:
        return True  # this never happens as there is always the implicit return None which is 2 instructions
    assert instructions[-1].opname == 'RETURN_VALUE'  # returns TOS (top of stack)
    instruction = instructions[-2]
    if not (instruction.opname == 'LOAD_CONST' and code_obj.co_consts[instruction.arg] is None):  # TOS is None
        return False  # return is not None
    instructions = instructions[:-2]
    if len(instructions) == 0:
        return True
    # look for raise NotImplementedError
    if instructions[-1].opname == 'RAISE_VARARGS':
        # the thing we are raising should be the result of __call__  (instantiating exception object)
        if instructions[-2].opname == 'CALL_FUNCTION':
            for instr in instructions[:-2]:
                if instr.opname == 'LOAD_GLOBAL' and code_obj.co_names[instr.arg] == 'NotImplementedError':
                    return True

    return False


_Instruction = collections.namedtuple('_Instruction', ('opcode', 'opname', 'arg', 'argval'))


def _get_instructions(code_obj):
    if hasattr(dis, 'get_instructions'):
        return list(dis.get_instructions(code_obj))

    instructions = []
    instruction = None
    for byte in code_obj.co_code:
        if instruction is None:
            instruction = [byte]
        else:
            instruction.append(byte)
        if instruction[0] < dis.HAVE_ARGUMENT or len(instruction) == 3:
            op_code = instruction[0]
            op_name = dis.opname[op_code]
            if instruction[0] < dis.HAVE_ARGUMENT:
                instructions.append(_Instruction(op_code, op_name, None, None))
            else:
                arg = instruction[1]
                instructions.append(_Instruction(op_code, op_name, arg, arg))
            instruction = None
    return instructions


def _is_descriptor(obj):  # in our context we only care about __get__
    return hasattr(obj, '__get__')


class _ParamTypes(object):
    def __init__(self, pos_only, pos_or_kw, vararg, kw_only, varkw):
        self.pos_only = pos_only
        self.pos_or_kw = pos_or_kw
        self.vararg = vararg
        self.kw_only = kw_only
        self.varkw = varkw
        self.positional = pos_only + pos_or_kw
        self.keyword = pos_or_kw + kw_only


def _signature_info(arg_spec):
    # type: (List[Parameter]) -> _ParamTypes
    param_types = collections.defaultdict(list)
    for param in arg_spec:
        param_types[param.kind].append(param)

    return _ParamTypes(param_types[Parameter.POSITIONAL_ONLY],
                       param_types[Parameter.POSITIONAL_OR_KEYWORD],
                       param_types[Parameter.VAR_POSITIONAL],
                       param_types[Parameter.KEYWORD_ONLY],
                       param_types[Parameter.VAR_KEYWORD]
                       )


def _required_params(param_list):
    """ return params without a default"""
    # params with defaults come last
    for i, p in enumerate(param_list):
        if p.default is not Parameter.empty:
            return param_list[:i]
    # no defaults
    return param_list


def _kw_names_match(func, base):
    func_names = set(p.name for p in func)
    return all(p.name in func_names for p in base)


def _positional_args_match(func_list, base_list, vararg, base_kwo):
    # arguments are positional - so name doesn't matter
    # func may not have fewer parameters
    if len(base_list) > len(func_list):
        if not vararg:  # unless it has varargs
            return False
    # extra parameters must be have defaults (be optional)
    base_kwo = [p.name for p in base_kwo]
    for p in func_list[len(base_list):]:
        if p.default is Parameter.empty and p.name not in base_kwo:
            return False
    return True


def _pos_or_kw_args_match(func_list, base_list, base_pos_only):
    # arguments names must occur in same order
    if base_pos_only and func_list and base_list:  # some args may be positional only in base method
        func_args = [p.name for p in func_list]
        base_args = [p.name for p in base_list]
        try:
            i = func_args.index(base_args[0])
        except ValueError:
            return False
        if i > len(base_pos_only):
            return False
        func_list = func_list[i:]
    for fp, bp in zip(func_list, base_list):
        if fp.name != bp.name:
            return False
    return True


def _keyword_args_match(func_list, base_list, varkw, num_pos):
    base_args = {p.name: p for p in base_list}
    for i, fp in enumerate(func_list):
        bp = base_args.get(fp.name, None)
        if i < num_pos:  # this argument is positional
            if bp is not None:
                return False
            continue
        if bp is None:  # new arg
            if fp.default is Parameter.empty:  # arg must have a default
                return False
        elif bp.default is not Parameter.empty:  # base has default
            if fp.default is Parameter.empty:  # func must have a default
                return False
    if not varkw:
        func_args = {p.name: p for p in func_list}
        for bp in base_list:
            if bp.name not in func_args:
                return False
    return True


def _signatures_are_consistent(func_sig, base_sig):
    # type: (Signature, Signature) -> bool
    """
    :param func_sig: Signature of overriding function
    :param base_sig: Signature of base class function
    :return: True if signature of func is Liskov substitutable for base.
    """
    base = _signature_info(base_sig.parameters.values())
    func = _signature_info(func_sig.parameters.values())

    if base.vararg and not func.vararg:
        return False
    if base.varkw and not func.varkw:
        return False

    if not _positional_args_match(func.positional, base.positional, func.vararg, base.kw_only):
        return False
    if not _pos_or_kw_args_match(func.pos_or_kw, base.pos_or_kw, base.pos_only):
        return False
    n = len(base.pos_only) - len(func.pos_only)
    if not _keyword_args_match(func.keyword, base.keyword, func.varkw, n):
        return False

    return True


def _ensure_everything_is_abstract(attributes):
    # all methods and properties are abstract on a pure interface
    namespace = {}
    functions = []
    interface_method_signatures = {}
    interface_attribute_names = set()
    for name, value in attributes.items():
        if _builtin_attrs(name):
            pass  # shortcut
        elif name == '__annotations__':
            interface_attribute_names.update(value.keys())
        elif value is None:
            interface_attribute_names.add(name)
            continue  # do not add to class namespace
        elif getattr(value, '__isabstractmethod__', False):
            if isinstance(value, (staticmethod, classmethod, types.FunctionType)):
                if isinstance(value, (staticmethod, classmethod)):
                    func = value.__func__
                else:
                    func = value
                functions.append(func)
                interface_method_signatures[name] = signature(func)
            elif isinstance(value, property):
                interface_attribute_names.add(name)
                continue  # do not add to class namespace
        elif isinstance(value, staticmethod):
            func = value.__func__
            functions.append(func)
            interface_method_signatures[name] = signature(func)
            value = abstractstaticmethod(func)
        elif isinstance(value, classmethod):
            func = value.__func__
            interface_method_signatures[name] = signature(func)
            functions.append(func)
            value = abstractclassmethod(func)
        elif isinstance(value, types.FunctionType):
            functions.append(value)
            interface_method_signatures[name] = signature(value)
            value = abstractmethod(value)
        elif isinstance(value, property):
            interface_attribute_names.add(name)
            functions.extend([value.fget, value.fset, value.fdel])  # may contain Nones
            continue  # do not add to class namespace
        else:
            raise InterfaceError('Interface class attributes must have a value of None\n{}={}'.format(name, value))
        namespace[name] = value
    return namespace, functions, interface_method_signatures, interface_attribute_names


def _check_method_signatures(attributes, clsname, interface_method_signatures):
    """ Scan attributes dict for interface method overrides and check the function signatures are consistent """
    for name, base_sig in interface_method_signatures.items():
        if name not in attributes:
            continue
        value = attributes[name]
        if not isinstance(value, (staticmethod, classmethod, types.FunctionType)):
            if _is_descriptor(value):
                continue
            else:
                raise InterfaceError('Interface method over-ridden with non-method')
        if isinstance(value, (staticmethod, classmethod)):
            func = value.__func__
        else:
            func = value
        func_sig = signature(func)
        if not _signatures_are_consistent(func_sig, base_sig):
            msg = '{module}.{clsname}.{name} arguments do not match base method'.format(
                module=attributes['__module__'], clsname=clsname, name=name)
            raise InterfaceError(msg)


def _do_missing_impl_warnings(cls, clsname):
    stacklevel = 2
    stack = inspect.stack()
    # walk up stack until we get out of pure_interface module
    while stacklevel < len(stack) and 'pure_interface' in stack[stacklevel][1]:
        stacklevel += 1
    # add extra levels for sub-meta-classes
    stack.pop(0)
    while stack and stack[0][0].f_code.co_name == '__new__':
        stacklevel += 1
        stack.pop(0)
    for method_name in cls.__abstractmethods__:
        message = 'Incomplete Implementation: {clsname} does not implement {method_name}'
        message = message.format(clsname=clsname, method_name=method_name)
        missing_method_warnings.append(message)
        warnings.warn(message, stacklevel=stacklevel)


def _structural_type_check(cls, instance):
    subclass = type(instance)
    for attr in cls._pi.interface_method_names:
        subtype_value = getattr(subclass, attr, None)
        if not callable(subtype_value):
            return False
    for attr in cls._pi.interface_attribute_names:
        if not hasattr(instance, attr):
            return False
    return True


def _class_structural_type_check(cls, subclass):
    if subclass in cls._pi.structural_subclasses:
        return True

    for attr in cls._pi.interface_method_names:
        subtype_value = getattr(subclass, attr, None)
        if not callable(subtype_value):
            return False
    for attr in cls._pi.interface_attribute_names:
        if not hasattr(subclass, attr):
            return False

    cls._pi.structural_subclasses.add(subclass)
    if is_development:
        stacklevel = 2
        stack = inspect.stack()
        while stacklevel < len(stack) and 'pure_interface' in stack[stacklevel-1][1]:
            stacklevel += 1
        warnings.warn('Class {module}.{sub_name} implements {cls_name}.\n'
                      'Consider inheriting {cls_name} or using {cls_name}.register({sub_name})'
                      .format(cls_name=cls.__name__, sub_name=subclass.__name__, module=subclass.__module__),
                      stacklevel=stacklevel)
    return True


def _get_adapter(cls, obj_type):
    # type: (Type[PI], Type[Any]) -> Optional[Callable]
    """ Returns a callable that adapts objects of type obj_type to this interface or None if no adapter exists.
    """
    adapters = {}
    candidate_interfaces = [cls] + cls.__subclasses__()
    candidate_interfaces.reverse()  # prefer this class over sub-class adapters
    for subcls in candidate_interfaces:
        if type_is_interface(subcls):
            adapters.update(subcls._pi.adapters)
    if not adapters:
        return None

    for obj_class in obj_type.__mro__:
        try:
            return adapters[obj_class]
        except KeyError:
            continue
    return None


class InterfaceType(abc.ABCMeta):
    """
    Meta-Class for Interface.
    This type:
        * determines if the new class is an interface or a concrete class.
        * if the type is an interface:
            * mark all methods and properties as abstract
            * ensure all method and property bodies are empty
        * optionally check overriding method signatures match those on base class.
        * if the type is a concrete class then patch the abstract properties with AttributeProperies.
    """

    def __new__(mcs, clsname, bases, attributes, **kwargs):
        # Interface is not in globals() when we are constructing the Interface class itself.
        has_interface = any(Interface in base.mro() for base in bases) if 'Interface' in globals() else True
        if not has_interface:
            # Don't interfere if meta class is only included to permit interface inheritance,
            # but no actual interface is being used.
            cls = super(InterfaceType, mcs).__new__(mcs, clsname, bases, attributes, **kwargs)
            cls._pi = _PIAttributes(False, (), {}, ())
            return cls

        base_types = [(cls, _type_is_interface(cls)) for cls in bases]
        type_is_interface = all(is_interface for cls, is_interface in base_types)

        if clsname == 'Interface' and attributes.get('__module__', '') == 'pure_interface':
            type_is_interface = True
        if len(bases) > 1 and bases[0] is object:
            warnings.warn('object should come after {} in base list of {}. '
                          'Fixing inconsistent MRO is deprecated'.format(bases[1].__name__, clsname))
            bases = bases[1:]  # create a consistent MRO order
            base_types = base_types[1:]

        interface_method_signatures = dict()
        interface_attribute_names = set()
        abstract_properties = set()
        for i in range(len(bases)-1, -1, -1):  # start at back end
            base, base_is_interface = base_types[i]
            if base is object:
                continue
            base_abstract_properties = _get_pi_attribute(base, 'abstractproperties', set())
            abstract_properties.update(base_abstract_properties)
            if base_is_interface:
                if hasattr(base, '_pi'):
                    method_signatures = _get_pi_attribute(base, 'interface_method_signatures', {})
                    attribute_names = _get_pi_attribute(base, 'interface_attribute_names', set())
                else:
                    attribute_names, method_signatures = _get_abc_interface_props_and_funcs(base)
                interface_method_signatures.update(method_signatures)
                interface_attribute_names.update(attribute_names)
            elif is_development and not issubclass(base, Interface):
                _check_method_signatures(base.__dict__, base.__name__, interface_method_signatures)

        if is_development:
            _check_method_signatures(attributes, clsname, interface_method_signatures)

        if type_is_interface:
            if 'PureInterface' in [b.__name__ for b in bases]:
                warnings.warn('PureInterface class has been renamed to Interface.')
            if clsname == 'Interface' and attributes.get('__module__', '') == 'pure_interface':
                namespace = attributes
                functions = []
                method_signatures = {}
                attribute_names = set()
            else:
                namespace, functions, method_signatures, attribute_names = _ensure_everything_is_abstract(attributes)
            partial_implementation = False
            interface_method_signatures.update(method_signatures)
            interface_attribute_names.update(attribute_names)
            abstract_properties.update(interface_attribute_names)
            unwrap = getattr(mcs, '_pi_unwrap_decorators', False)
            for func in functions:
                if func is None:
                    continue
                if not _is_empty_function(func, unwrap):
                    raise InterfaceError('Function "{}" is not empty.\n'
                                         'Did you forget to inherit from object to make the class concrete?'.format(func.__name__))
        else:  # concrete sub-type
            namespace = attributes
            class_properties = set()
            for bt, is_interface in base_types:
                if not is_interface:
                    class_properties |= set(k for k, v in bt.__dict__.items() if _is_descriptor(v))
            class_properties |= set(k for k, v in namespace.items() if _is_descriptor(v))
            abstract_properties.difference_update(class_properties)
            partial_implementation = 'pi_partial_implementation' in namespace
            if partial_implementation:
                value = namespace.pop('pi_partial_implementation')
                if not value:
                    warnings.warn('Partial implementation is indicated by presence of '
                                  'pi_partial_implementation attribute, not it''s value')

        # create class
        cls = super(InterfaceType, mcs).__new__(mcs, clsname, bases, namespace, **kwargs)
        cls._pi = _PIAttributes(type_is_interface, abstract_properties,
                                interface_method_signatures, interface_attribute_names)

        # warnings
        if not type_is_interface and is_development and cls.__abstractmethods__ and not partial_implementation:
            _do_missing_impl_warnings(cls, clsname)

        return cls

    def __call__(cls, *args, **kwargs):
        """ Check that abstract properties are created in constructor """
        if cls._pi.type_is_interface:
            raise InterfaceError('Interfaces cannot be instantiated')
        self = super(InterfaceType, cls).__call__(*args, **kwargs)
        for attr in cls._pi.abstractproperties:
            if not (hasattr(cls, attr) or hasattr(self, attr)):
                # check for attribute on class first so that properties are not run.
                raise InterfaceError('{}.__init__ does not create required attribute "{}"'.format(cls.__name__, attr))
        return self

    def __dir__(cls):
        listing = set(cls._pi.interface_attribute_names)
        for base in cls.mro():
            listing.update(base.__dict__.keys())
        listing = sorted(listing)
        return listing

    def provided_by(cls, obj, allow_implicit=True):
        if not cls._pi.type_is_interface:
            raise InterfaceError('provided_by() can only be called on interfaces')
        if isinstance(obj, cls):
            return True
        if not allow_implicit:
            return False
        if _class_structural_type_check(cls, type(obj)):
            return True
        return _structural_type_check(cls, obj)

    def interface_only(cls, implementation):
        if cls._pi.impl_wrapper_type is None:
            type_name = '_{}Only'.format(cls.__name__)
            attributes = {'__module__': cls.__module__}
            if '__call__' in cls._pi.interface_names:
                attributes['__call__'] = getattr(implementation, '__call__')
            cls._pi.impl_wrapper_type = type(type_name, (_ImplementationWrapper,), attributes)
            abc.ABCMeta.register(cls, cls._pi.impl_wrapper_type)
        return cls._pi.impl_wrapper_type(implementation, cls)

    def adapt(cls, obj, allow_implicit=False, interface_only=None):
        if interface_only is None:
            interface_only = is_development
        if isinstance(obj, _ImplementationWrapper):
            obj = obj._ImplementationWrapper__impl
        if InterfaceType.provided_by(cls, obj, allow_implicit=allow_implicit):
            adapter = no_adaption
        else:
            adapter = _get_adapter(cls, type(obj))
            if adapter is None:
                raise AdaptionError('Cannot adapt {} to {}'.format(obj, cls.__name__))

        adapted = adapter(obj)
        if not InterfaceType.provided_by(cls, adapted, allow_implicit):
            raise AdaptionError('Adapter {} does not implement interface {}'.format(adapter, cls.__name__))
        if interface_only:
            adapted = InterfaceType.interface_only(cls, adapted)
        return adapted

    def adapt_or_none(cls, obj, allow_implicit=False, interface_only=None):
        try:
            return InterfaceType.adapt(cls, obj, allow_implicit=allow_implicit, interface_only=interface_only)
        except AdaptionError:
            return None

    def can_adapt(cls, obj, allow_implicit=False):
        try:
            InterfaceType.adapt(cls, obj, allow_implicit=allow_implicit)
        except AdaptionError:
            return False
        return True

    def filter_adapt(cls, objects, allow_implicit=False, interface_only=None):
        for obj in objects:
            try:
                f = InterfaceType.adapt(cls, obj, allow_implicit=allow_implicit, interface_only=interface_only)
            except AdaptionError:
                continue
            yield f

    def optional_adapt(cls, obj, allow_implicit=False, interface_only=None):
        if obj is None:
            return None
        return InterfaceType.adapt(cls, obj, allow_implicit=allow_implicit, interface_only=interface_only)


class Interface(abc.ABC, metaclass=InterfaceType):
    # These methods don't need to be here, as they would resolve to the meta-class methods anyway.
    # However including them here means we can add type hints that would otherwise be ambiguous on the meta-class.

    @classmethod
    def provided_by(cls, obj, allow_implicit=True):
        # type: (Any, bool) -> bool
        """ Returns True if obj provides this interface.
        provided_by(cls, obj) is equivalent to isinstance(obj, cls) unless allow_implicit is True
        If allow_implicit is True then returns True if interface duck-type check passes.
        Returns False otherwise.
        """
        return InterfaceType.provided_by(cls, obj, allow_implicit=allow_implicit)

    @classmethod
    def interface_only(cls, implementation):
        # type: (Type[PI], PI) -> PI
        """ Returns a wrapper around implementation that provides ONLY this interface. """
        return InterfaceType.interface_only(cls, implementation)

    @classmethod
    def adapt(cls, obj, allow_implicit=False, interface_only=None):
        # type: (Type[PI], Any, bool, Optional[bool]) -> PI
        """ Adapts obj to interface, returning obj if to_interface.provided_by(obj, allow_implicit) is True
        and raising ValueError if no adapter is found
        If interface_only is True, or interface_only is None and is_development is True then the
        returned object is wrapped by an object that only provides the methods and properties defined by to_interface.
        """
        return InterfaceType.adapt(cls, obj, allow_implicit=allow_implicit, interface_only=interface_only)

    @classmethod
    def adapt_or_none(cls, obj, allow_implicit=False, interface_only=None):
        # type: (Type[PI], Any, bool, Optional[bool]) -> Optional[PI]
        """ Adapt obj to to_interface or return None if adaption fails """
        return InterfaceType.adapt_or_none(cls, obj, allow_implicit=allow_implicit, interface_only=interface_only)

    @classmethod
    def can_adapt(cls, obj, allow_implicit=False):
        # type: (Any, bool) -> bool
        """ Returns True if adapt(obj, allow_implicit) will succeed."""
        return InterfaceType.can_adapt(cls, obj, allow_implicit=allow_implicit)

    @classmethod
    def filter_adapt(cls, objects, allow_implicit=False, interface_only=None):
        # type: (Type[PI], Iterable[Any], bool, Optional[bool]) -> Iterable[PI]
        """ Generates adaptions of the given objects to this interface.
        Objects that cannot be adapted to this interface are silently skipped.
        """
        return InterfaceType.filter_adapt(cls, objects, allow_implicit=allow_implicit,
                                          interface_only=interface_only)

    @classmethod
    def optional_adapt(cls, obj, allow_implicit=False, interface_only=None):
        # type: (Type[PI], Any, bool, Optional[bool]) -> Optional[PI]
        """ Adapt obj to to_interface or return None if adaption fails """
        return InterfaceType.optional_adapt(cls, obj, allow_implicit=allow_implicit, interface_only=interface_only)


class PureInterface(Interface):
    # class for backwards compatibility
    pass


# adaption
def adapts(from_type, to_interface=None):
    # type: (Any, Type[PI]) -> Callable[[Any], Any]
    """Class or function decorator for declaring an adapter from a type to an interface.
    E.g.
        @adapts(MyClass, MyInterface)
        def interface_factory(obj):
            ....

    If decorating a class to_interface may be None to use the first interface in the class's MRO.
    E.g.
        @adapts(MyClass)
        class MyClassToInterfaceAdapter(MyInterface, object):
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


def register_adapter(adapter, from_type, to_interface):
    # type: (Callable, Any, Type[Interface]) -> None
    """ Registers adapter to convert instances of from_type to objects that provide to_interface
    for the to_interface.adapt() method.

    :param adapter: callable that takes an instance of from_type and returns an object providing to_interface.
    :param from_type: a type to adapt from
    :param to_interface: a (non-concrete) Interface subclass to adapt to.
    """
    if not callable(adapter):
        raise AdaptionError('adapter must be callable')
    if not isinstance(from_type, type):
        raise AdaptionError('{} must be a type'.format(from_type))
    if not (isinstance(to_interface, type) and _get_pi_attribute(to_interface, 'type_is_interface', False)):
        raise AdaptionError('{} is not an interface'.format(to_interface))
    adapters = _get_pi_attribute(to_interface, 'adapters')
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

    def adapt(self, obj, interface):
        """ Adapts `obj` to `interface`"""
        try:
            return self._adapters[interface][obj]
        except KeyError:
            return self._adapt(obj, interface)

    def adapt_or_none(self, obj, interface):
        """ Adapt obj to interface returning None on failure."""
        try:
            return self.adapt(obj, interface)
        except ValueError:
            return None

    def clear(self):
        """ Clears the cached adapters."""
        self._adapters = self._factory()

    def _adapt(self, obj, interface):
        adapted = interface.adapt(obj)
        try:
            adapters = self._adapters[interface]
        except KeyError:
            adapters = self._adapters[interface] = self._factory()
        adapters[obj] = adapted
        return adapted


def type_is_interface(cls):
    # type: (Type[Any]) -> bool
    """ Return True if cls is a pure interface"""
    try:
        if not issubclass(cls, Interface):
            return False
    except TypeError:  # handle non-classes
        return False
    return _get_pi_attribute(cls, 'type_is_interface', False)


def type_is_pure_interface(cls):
    warnings.warn('type_is_pure_interface has been renamed to type_is_interface.')
    return type_is_pure_interface(cls)


def get_type_interfaces(cls):
    # type: (Type[Any]) -> List[Type[Interface]]
    """ Returns all interfaces in the cls mro including cls itself if it is an interface """
    try:
        bases = cls.mro()
    except AttributeError:  # handle non-classes
        return []
    return [base for base in bases if type_is_interface(base) and base is not Interface]


def get_interface_names(interface):
    # type: (Type[Interface]) -> FrozenSet[str]
    """ returns a frozen set of names (methods and attributes) defined by the interface.
    if interface is not a Interface subtype then an empty set is returned.
    """
    if type_is_interface(interface):
        return _get_pi_attribute(interface, 'interface_names')
    else:
        return frozenset()


def get_interface_method_names(interface):
    # type: (Type[Interface]) -> FrozenSet[str]
    """ returns a frozen set of names of methods defined by the interface.
    if interface is not a Interface subtype then an empty set is returned
    """
    if type_is_interface(interface):
        return _get_pi_attribute(interface, 'interface_method_names')
    else:
        return frozenset()


def get_interface_attribute_names(interface):
    # type: (Type[Interface]) -> FrozenSet[str]
    """ returns a frozen set of names of attributes defined by the interface
    if interface is not a Interface subtype then an empty set is returned
    """
    if type_is_interface(interface):
        return _get_pi_attribute(interface, 'interface_attribute_names')
    else:
        return frozenset()


def _interface_from_anno(annotation):
    """ Typically the annotation is the interface,  but if a default value of None is given the annotation is
    a typing.Union[interface, None] a.k.a. Optional[interface]. Lets be nice and support those too.
    """
    try:
        if issubclass(annotation, Interface):
            return annotation
    except TypeError:
        pass
    if hasattr(annotation, '__origin__') and hasattr(annotation, '__args__'):
        # could be a typing.Union
        if annotation.__origin__ is not typing.Union:
            return None
        for arg_type in annotation.__args__:
            try:
                if issubclass(arg_type, Interface):
                    return arg_type
            except TypeError:
                pass

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
        if annotations is None:
            annotations = {}
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
        try:
            can_adapt = issubclass(i_face, Interface)
        except TypeError:
            can_adapt = False
        if not can_adapt:
            raise AdaptionError('adapt_args parameter values must be subtypes of Interface')
    return decorator


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

except ImportError:
    pass
