"""
pure_interface enforces empty functions and properties on interfaces and provides adaption and structural type checking.
"""
from __future__ import absolute_import, division, print_function

import abc
from abc import abstractclassmethod, abstractmethod, abstractstaticmethod
import collections
import dis
import functools
import inspect
from inspect import Parameter, signature, Signature
import sys
import types
from typing import Any, Callable, Dict, FrozenSet, Generic, Iterable, List, Optional, Set, Tuple, Type, TypeVar
import warnings
import weakref

from .errors import AdaptionError, InterfaceError

is_development = not hasattr(sys, 'frozen')
missing_method_warnings: List[str] = []

_T = TypeVar('_T')


def set_is_development(is_dev: bool) -> None:
    global is_development
    is_development = is_dev


def get_is_development() -> bool:
    return is_development


def get_missing_method_warnings() -> List[str]:
    return missing_method_warnings


def no_adaption(obj: _T) -> _T:
    return obj


AnInterface = TypeVar('AnInterface', bound='Interface')
AnInterfaceType = TypeVar('AnInterfaceType', bound='InterfaceType')


class _PIAttributes:
    """ rather than clutter the class namespace with lots of _pi_XXX attributes, collect them all here"""

    def __init__(self, this_type_is_an_interface: bool,
                 abstract_properties: Set[str],
                 interface_method_signatures: Dict[str, Signature],
                 interface_attribute_names: List[str]):
        self.type_is_interface: bool = this_type_is_an_interface
        # abstractproperties are checked for at instantiation.
        # When concrete classes use a @property then they are removed from this set
        self.abstractproperties = frozenset(abstract_properties)
        self.interface_method_names = frozenset(interface_method_signatures.keys())
        # keep an ordered list for dataclass
        attr_names = []
        seen = set()
        for name in interface_attribute_names:
            if name not in seen:
                attr_names.append(name)
                seen.add(name)
        self.interface_attribute_names: List[str] = attr_names
        self.interface_method_signatures = interface_method_signatures
        self.adapters = weakref.WeakKeyDictionary()  # type: ignore
        self.registered_types = weakref.WeakSet()  # type: ignore
        self.structural_subclasses: Set[type] = set()
        self.impl_wrapper_type: Optional[type] = None

    @property
    def interface_names(self) -> FrozenSet[str]:
        return self.interface_method_names.union(self.interface_attribute_names)


class _ImplementationWrapper:
    def __init__(self, implementation: Any, interface: AnInterfaceType):
        object.__setattr__(self, '_ImplementationWrapper__impl', implementation)
        object.__setattr__(self, '_ImplementationWrapper__interface', interface)
        object.__setattr__(self, '_ImplementationWrapper__interface_attrs', interface._pi.interface_names)
        object.__setattr__(self, '_ImplementationWrapper__interface_name', interface.__name__)

    def __getattr__(self, attr: str) -> Any:
        impl = self.__impl
        if attr in self.__interface_attrs:
            return getattr(impl, attr)
        else:
            raise AttributeError("'{}' interface has no attribute '{}'".format(self.__interface_name, attr))

    def __setattr__(self, key: str, value: Any) -> None:
        if key in self.__interface_attrs:
            setattr(self.__impl, key, value)
        else:
            raise AttributeError("'{}' interface has no attribute '{}'".format(self.__interface_name, key))


def _builtin_attrs(name: str) -> bool:
    """ These attributes are ignored when checking ABC types for emptyness.
    """
    return name in ('__doc__', '__module__', '__qualname__', '__abstractmethods__', '__dict__',
                    '__metaclass__', '__weakref__', '__subclasshook__', '__orig_bases__',
                    '_abc_cache', '_abc_impl', '_abc_registry', '_abc_negative_cache_version', '_abc_negative_cache',
                    '_pi', '_pi_unwrap_decorators')


def get_pi_attribute(cls: Type, attr_name: str, default: Any = None) -> Any:
    if hasattr(cls, '_pi'):
        return getattr(cls._pi, attr_name)
    else:
        return default


def _type_is_interface(cls: type) -> bool:
    """ Return True if cls is a pure interface or an empty ABC class"""
    if cls is object:
        return False
    if hasattr(cls, '_pi'):
        return cls._pi.type_is_interface
    if cls is Generic:
        return True  # this class is just for type hinting
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


def _get_abc_interface_props_and_funcs(cls: Type[abc.ABC]) -> Tuple[Set[str], Dict[str, Signature]]:
    properties: Set[str] = set()
    function_sigs: Dict[str, Signature] = {}
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


def _unwrap_function(func: Any) -> Any:
    """ Look for decorated functions and return the wrapped function.
    """
    while hasattr(func, '__wrapped__'):
        func = func.__wrapped__
    return func


def _is_empty_function(func: Any, unwrap: bool = False) -> bool:
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
    byte_code = code_obj.co_code
    if byte_code.startswith(b'\x81\x01'):
        byte_code = byte_code[2:]  # remove GEN_START async def opcode
    if byte_code.startswith(b'\x97\x00'):
        byte_code = byte_code[2:]  # remove RESUME opcode added in 3.11
    if byte_code.startswith(b'\t\x00'):
        byte_code = byte_code[2:]  # remove NOP opcode
    if byte_code.startswith(b'K\x00'):
        byte_code = byte_code[2:]  # remove RETURN_GENERATOR async def opcode in py311
        if byte_code.startswith(b'\x01'):
            byte_code = byte_code[2:]  # remove POP_TOP
    if byte_code.startswith(b'\x97\x00'):
        byte_code = byte_code[2:]  # remove RESUME opcode added in 3.11
    if byte_code.startswith(b'\t\x00'):
        byte_code = byte_code[2:]  # remove NOP opcode
    if byte_code in (b'd\x00\x00S', b'd\x00S\x00') and code_obj.co_consts[0] is None:
        return True
    if byte_code in (b'd\x01\x00S', b'd\x01S\x00') and code_obj.co_consts[1] is None:
        return True
    if byte_code == b'y\x00' and code_obj.co_consts[0] is None:  # RETURN_CONST in 3.12+
        return True
    # convert bytes to instructions
    instructions = list(dis.get_instructions(code_obj))
    if len(instructions) < 2:
        return True  # this never happens
    if instructions[0].opname == 'GEN_START':
        instructions.pop(0)
    if instructions[0].opname == 'RESUME':
        instructions.pop(0)
    if instructions[0].opname == 'NOP':
        instructions.pop(0)
    if instructions[0].opname == 'RETURN_GENERATOR':
        instructions.pop(0)
        if instructions[0].opname == 'POP_TOP':
            instructions.pop(0)
        # All generator functions end with these 2 opcodes in 3.12+
        if (len(instructions) > 2 and
                instructions[-2].opname == 'CALL_INTRINSIC_1' and
                instructions[-1].opname == 'RERAISE'):
            instructions = instructions[:-2]  # remove last 2 instructions
    if instructions[0].opname == 'RESUME':
        instructions.pop(0)
    if instructions[0].opname == 'NOP':
        instructions.pop(0)
    if instructions[-1].opname == 'RETURN_VALUE':  # returns TOS (top of stack)
        instruction = instructions[-2]
        if not (instruction.opname == 'LOAD_CONST' and code_obj.co_consts[instruction.arg] is None):  # TOS is None
            return False  # return is not None
        instructions = instructions[:-2]
    if len(instructions) > 0 and instructions[-1].opname == 'RETURN_CONST' and instructions[-1].argval is None:  # returns constant
        instructions.pop(-1)
    if len(instructions) == 0:
        return True
    # look for raise NotImplementedError
    if instructions[-1].opname == 'RAISE_VARARGS':
        # the thing we are raising should be the result of __call__  (instantiating exception object)
        if instructions[-2].opname in ('CALL_FUNCTION', 'CALL'):
            for instr in instructions[-3::-1]:
                if instr.opname == 'LOAD_GLOBAL':
                    return bool(instr.argval == 'NotImplementedError')

    return False


def _is_descriptor(obj: Any) -> bool:  # in our context we only care about __get__
    return hasattr(obj, '__get__')


class _ParamTypes:
    def __init__(self, pos_only: List[Parameter], pos_or_kw: List[Parameter],
                 vararg: List[Parameter], kw_only: List[Parameter], varkw: List[Parameter]):
        self.pos_only = pos_only
        self.pos_or_kw = pos_or_kw
        self.vararg = vararg
        self.kw_only = kw_only
        self.varkw = varkw
        self.positional = pos_only + pos_or_kw
        self.keyword = pos_or_kw + kw_only


def _signature_info(arg_spec: Iterable[Parameter]) -> _ParamTypes:
    param_types = collections.defaultdict(list)
    for param in arg_spec:
        param_types[param.kind].append(param)

    return _ParamTypes(param_types[Parameter.POSITIONAL_ONLY],
                       param_types[Parameter.POSITIONAL_OR_KEYWORD],
                       param_types[Parameter.VAR_POSITIONAL],
                       param_types[Parameter.KEYWORD_ONLY],
                       param_types[Parameter.VAR_KEYWORD]
                       )


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


def _signatures_are_consistent(func_sig: Signature, base_sig: Signature) -> bool:
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
    functions: List[Optional[Callable]] = []
    interface_method_signatures = {}
    interface_attribute_names = []
    for name, value in attributes.items():
        if _builtin_attrs(name):
            pass  # shortcut
        elif name == '__annotations__':
            interface_attribute_names.extend(value.keys())
        elif value is None:
            interface_attribute_names.append(name)
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
                interface_attribute_names.append(name)
                continue  # do not add to class namespace
        elif isinstance(value, staticmethod):
            func = value.__func__
            functions.append(func)
            interface_method_signatures[name] = signature(func)
            value = staticmethod(abstractmethod(func))
        elif isinstance(value, classmethod):
            func = value.__func__
            interface_method_signatures[name] = signature(func)
            functions.append(func)
            value = classmethod(abstractmethod(func))
        elif isinstance(value, types.FunctionType):
            functions.append(value)
            interface_method_signatures[name] = signature(value)
            value = abstractmethod(value)
        elif isinstance(value, functools.singledispatchmethod):
            func = value.func
            functions.append(func)
            interface_method_signatures[name] = signature(func)
            value = func  # ignore the singledispatchmethod decorator
        elif isinstance(value, property):
            interface_attribute_names.append(name)
            functions.extend([value.fget, value.fset, value.fdel])  # may contain Nones
            continue  # do not add to class namespace
        else:
            raise InterfaceError('Interface class attributes must have a value of None\n{}={}'.format(name, value))
        namespace[name] = value
    return namespace, functions, interface_method_signatures, interface_attribute_names


def _ensure_annotations(names, namespace, base_interfaces):
    # annotations need to be kept in order for dataclass decorator
    # we only want dataclass annotations for attributes that don't already exist
    annotations: Dict[str, Any] = {}
    base_annos: Dict[str, Any] = {}
    for base in reversed(base_interfaces):
        base_annos.update(getattr(base, '__annotations__', {}))
    for name in names:
        if name not in annotations and name not in namespace:
            annotations[name] = base_annos.get(name, Any)
    annotations.update(namespace.get('__annotations__', {}))
    namespace['__annotations__'] = annotations


def _check_method_signatures(attributes, clsname, interface_method_signatures):
    """ Scan attributes dict for interface method overrides and check the function signatures are consistent """
    for name, base_sig in interface_method_signatures.items():
        if name not in attributes:
            continue
        value = attributes[name]
        if not isinstance(value, (staticmethod, classmethod, types.FunctionType, functools.singledispatchmethod)):
            if _is_descriptor(value):
                continue
            else:
                raise InterfaceError('Interface method over-ridden with non-method')
        if isinstance(value, (staticmethod, classmethod)):
            func = value.__func__
        elif isinstance(value, functools.singledispatchmethod):
            func = value.func
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
        while stacklevel < len(stack) and 'pure_interface' in stack[stacklevel - 1][1]:
            stacklevel += 1
        warnings.warn('Class {module}.{sub_name} implements {cls_name}.\n'
                      'Consider inheriting {cls_name} or using {cls_name}.register({sub_name})'
                      .format(cls_name=cls.__name__, sub_name=subclass.__name__, module=subclass.__module__),
                      stacklevel=stacklevel)
    return True


def _get_adapter(cls: AnInterfaceType, obj_type: Type) -> Optional[Callable]:
    """ Returns a callable that adapts objects of type obj_type to this interface or None if no adapter exists.
    """
    adapters = {}  # type: ignore
    # registered interfaces can come from cls.register(AnotherInterface) or @sub_interface_of(AnotherInterface)(cls)
    candidate_interfaces = [cls] + cls.__subclasses__() + list(cls._pi.registered_types)
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
    _pi: _PIAttributes

    def __new__(mcs, clsname, bases, attributes, **kwargs):
        # Interface is not in globals() when we are constructing the Interface class itself.
        has_interface = any(Interface in base.mro() for base in bases) if 'Interface' in globals() else True
        if not has_interface:
            # Don't interfere if meta class is only included to permit interface inheritance,
            # but no actual interface is being used.
            cls = super(InterfaceType, mcs).__new__(mcs, clsname, bases, attributes, **kwargs)
            cls._pi = _PIAttributes(False, set(), {}, [])
            return cls

        base_types = [(cls, _type_is_interface(cls)) for cls in bases]

        if clsname == 'Interface' and attributes.get('__module__', '') == 'pure_interface.interface':
            this_type_is_an_interface = True
        else:
            assert 'Interface' in globals()
            this_type_is_an_interface = Interface in bases
            if this_type_is_an_interface and not all(is_interface for cls, is_interface in base_types):
                raise InterfaceError('All bases must be interface types when declaring an interface')
        interface_method_signatures = dict()
        interface_attribute_names = list()
        abstract_properties = set()
        for i in range(len(bases) - 1, -1, -1):  # start at back end
            base, base_is_interface = base_types[i]
            if base is object:
                continue
            base_abstract_properties = get_pi_attribute(base, 'abstractproperties', set())
            abstract_properties.update(base_abstract_properties)
            if base_is_interface:
                if hasattr(base, '_pi'):
                    method_signatures = get_pi_attribute(base, 'interface_method_signatures', {})
                    attribute_names = get_pi_attribute(base, 'interface_attribute_names', [])
                else:
                    attribute_names, method_signatures = _get_abc_interface_props_and_funcs(base)
                interface_method_signatures.update(method_signatures)
                interface_attribute_names.extend(attribute_names)
            elif is_development and not issubclass(base, Interface):
                _check_method_signatures(base.__dict__, base.__name__, interface_method_signatures)

        if is_development:
            _check_method_signatures(attributes, clsname, interface_method_signatures)

        base_interfaces = [bt for bt, is_interface in base_types if is_interface]
        if interface_attribute_names and base_interfaces:
            # provide interface attributes as annotations so that dataclass decorator creates all attributes
            # defined on base interfaces.
            _ensure_annotations(interface_attribute_names, attributes, base_interfaces)

        if this_type_is_an_interface:
            if clsname == 'Interface' and attributes.get('__module__', '') == 'pure_interface.interface':
                namespace = attributes
                functions = []
                method_signatures = {}
                attribute_names = []
            else:
                namespace, functions, method_signatures, attribute_names = _ensure_everything_is_abstract(attributes)
            partial_implementation = False
            interface_method_signatures.update(method_signatures)
            interface_attribute_names.extend(attribute_names)
            abstract_properties.update(interface_attribute_names)
            unwrap = getattr(mcs, '_pi_unwrap_decorators', False)
            for func in functions:
                if func is None:
                    continue
                if not _is_empty_function(func, unwrap):
                    raise InterfaceError('Interface method "{}.{}" must be empty.'.format(
                        clsname, func.__name__))
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
        namespace['_pi'] = _PIAttributes(this_type_is_an_interface, abstract_properties,
                                         interface_method_signatures, interface_attribute_names)
        cls = super(InterfaceType, mcs).__new__(mcs, clsname, bases, namespace, **kwargs)

        # warnings
        if not this_type_is_an_interface and is_development and cls.__abstractmethods__ and not partial_implementation:
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
        return sorted(listing)

    def provided_by(cls, obj):
        return cls._provided_by(obj, allow_implicit=True)

    def _provided_by(cls, obj, allow_implicit=True):
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
        adapter: Optional[Callable[[Any], 'InterfaceType']]
        if InterfaceType._provided_by(cls, obj, allow_implicit=allow_implicit):
            adapter = no_adaption
        else:
            adapter = _get_adapter(cls, type(obj))
            if adapter is None:
                raise AdaptionError('Cannot adapt {} to {}'.format(obj, cls.__name__))

        adapted = adapter(obj)
        if not InterfaceType._provided_by(cls, adapted, allow_implicit):
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

    def register(cls, subclass: Type[_T]) -> Type[_T]:
        if type_is_interface(cls):
            cls._pi.registered_types.add(subclass)  # type: ignore[attr-defined]
        return super().register(subclass)


class Interface(abc.ABC, metaclass=InterfaceType):
    # These methods don't need to be here, as they would resolve to the meta-class methods anyway.
    # However, including them here means we can add type hints that would otherwise be ambiguous on the meta-class.
    _pi: _PIAttributes

    @classmethod
    def provided_by(cls, obj) -> bool:
        """ Returns True if obj provides this interface (structural type-check).
        """
        return InterfaceType.provided_by(cls, obj)

    @classmethod
    def interface_only(cls: Type[AnInterface], implementation: AnInterface) -> AnInterface:
        """ Returns a wrapper around implementation that provides ONLY this interface. """
        return InterfaceType.interface_only(cls, implementation)

    @classmethod
    def adapt(cls: Type[AnInterface], obj: Any,
              allow_implicit: bool = False, interface_only: Optional[bool] = None) -> AnInterface:
        """ Adapts obj to interface, returning obj if to_interface.provided_by(obj, allow_implicit) is True
        and raising ValueError if no adapter is found
        If interface_only is True, or interface_only is None and is_development is True then the
        returned object is wrapped by an object that only provides the methods and properties defined by to_interface.
        """
        return InterfaceType.adapt(cls, obj, allow_implicit=allow_implicit, interface_only=interface_only)

    @classmethod
    def adapt_or_none(cls: Type[AnInterface], obj,
                      allow_implicit: bool = False, interface_only: Optional[bool] = None) -> Optional[AnInterface]:
        """ Adapt obj to to_interface or return None if adaption fails """
        return InterfaceType.adapt_or_none(cls, obj, allow_implicit=allow_implicit, interface_only=interface_only)

    @classmethod
    def can_adapt(cls, obj, allow_implicit: bool = False) -> bool:
        """ Returns True if adapt(obj, allow_implicit) will succeed."""
        return InterfaceType.can_adapt(cls, obj, allow_implicit=allow_implicit)

    @classmethod
    def filter_adapt(cls: Type[AnInterface], objects: Iterable,
                     allow_implicit: bool = False, interface_only: Optional[bool] = None) -> Iterable[AnInterface]:
        """ Generates adaptions of the given objects to this interface.
        Objects that cannot be adapted to this interface are silently skipped.
        """
        return InterfaceType.filter_adapt(cls, objects, allow_implicit=allow_implicit,
                                          interface_only=interface_only)

    @classmethod
    def optional_adapt(cls: Type[AnInterface], obj,
                       allow_implicit: bool = False, interface_only: Optional[bool] = None) -> Optional[AnInterface]:
        """ Adapt obj to to_interface or return None if adaption fails """
        return InterfaceType.optional_adapt(cls, obj, allow_implicit=allow_implicit, interface_only=interface_only)


def type_is_interface(cls: Type) -> bool:  # -> TypeGuard[AnInterfaceType]
    """ Return True if cls is a pure interface"""
    try:
        if not issubclass(cls, Interface):
            return False
    except TypeError:  # handle non-classes
        return False
    return get_pi_attribute(cls, 'type_is_interface', False)


def get_type_interfaces(cls: Type) -> List[type]:
    """ Returns all interfaces in the cls mro including cls itself if it is an interface """
    try:
        bases = cls.mro()
    except AttributeError:  # handle non-classes
        return []
    # type_is_interface ensures returned types are Interface subclasses by mypy doesn't know this
    return [base for base in bases if type_is_interface(base) and base is not Interface]


def get_interface_names(interface: Type) -> FrozenSet[str]:
    """ returns a frozen set of names (methods and attributes) defined by the interface.
    if interface is not a Interface subtype then an empty set is returned.
    """
    if type_is_interface(interface):
        return get_pi_attribute(interface, 'interface_names')
    else:
        return frozenset()


def get_interface_method_names(interface: Type) -> FrozenSet[str]:
    """ returns a frozen set of names of methods defined by the interface.
    if interface is not a Interface subtype then an empty set is returned
    """
    if type_is_interface(interface):
        return get_pi_attribute(interface, 'interface_method_names')
    else:
        return frozenset()


def get_interface_attribute_names(interface: Type) -> FrozenSet[str]:
    """ returns a frozen set of names of attributes defined by the interface
    if interface is not a Interface subtype then an empty set is returned
    """
    if type_is_interface(interface):
        return frozenset(get_pi_attribute(interface, 'interface_attribute_names', ()))
    else:
        return frozenset()

