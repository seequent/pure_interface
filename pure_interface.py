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
import collections
import dis
import inspect
import types
import sys
import warnings
import weakref

import six

__version__ = '2.1.0'


IS_DEVELOPMENT = not hasattr(sys, 'frozen')
missing_method_warnings = []

if six.PY2:
    _six_ord = ord
    ArgSpec = inspect.ArgSpec
    getargspec = inspect.getargspec
else:
    _six_ord = lambda x: x
    ArgSpec = collections.namedtuple('ArgSpec', 'args varargs keywords defaults')

    def getargspec(func):
        # getargspec is deprecated, but getfullargspec is not a drop-in replacement as advertised
        # as the keywords attribute has been renamed
        full_spec = inspect.getfullargspec(func)
        return ArgSpec(*full_spec[:4])


class InterfaceError(Exception):
    pass


class _PIAttributes(object):
    """ rather than clutter the class namespace with lots of _pi_XXX attributes, collect them all here"""
    def __init__(self, type_is_interface, interface_method_signatures, interface_property_names):
        self.type_is_pure_interface = type_is_interface
        self.abstractproperties = frozenset()  # properties that must be provided by instances
        self.interface_method_names = frozenset(interface_method_signatures.keys())
        self.interface_property_names = frozenset(interface_property_names)
        self.interface_method_signatures = interface_method_signatures
        self.adapters = weakref.WeakKeyDictionary()
        self.ducktype_subclasses = set()
        self.impl_wrapper_type = None


class AttributeProperty(object):
    """ Property that stores it's value in the instance dict under the same name.
        Abstract properties for concrete classes are replaced with these in the type definition to allow
        implementations to use attributes.
    """
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


class _ImplementationWrapper(object):
    def __init__(self, implementation, interface):
        self.__impl = implementation
        self.__interface = interface
        self.__method_names = interface._pi.interface_method_names
        self.__property_names = interface._pi.interface_property_names
        self.__interface_name = interface.__name__

    def __getattr__(self, attr):
        impl = self.__impl
        if attr in self.__method_names:
            return getattr(impl, attr)
        elif attr in self.__property_names:
            return getattr(impl, attr)
        else:
            raise AttributeError("'{}' interface has no attribute '{}'".format(self.__interface_name, attr))


def _builtin_attrs(name):
    """ These attributes are ignored when checking ABC types for emptyness.
    """
    return name in ('__doc__', '__module__', '__qualname__', '__abstractmethods__', '__dict__',
                    '__metaclass__', '__weakref__',
                    '_abc_cache', '_abc_registry', '_abc_negative_cache_version', '_abc_negative_cache')


def _get_pi_attribute(cls, attr_name, default=None):
    if hasattr(cls, '_pi'):
        return getattr(cls._pi, attr_name)
    else:
        return default


def _type_is_pure_interface(cls):
    """ Return True if cls is a pure interface or an empty ABC class"""
    if cls is object:
        return False
    if hasattr(cls, '_pi'):
        return cls._pi.type_is_pure_interface
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
            func = six.get_method_function(value)
            function_sigs[name] = getargspec(func)
        elif isinstance(value, types.FunctionType):
            function_sigs[name] = getargspec(value)
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
        func = six.get_method_function(func)
    if isinstance(func, property):
        func = property.fget
    if unwrap:
        func = _unwrap_function(func)
    try:
        code_obj = six.get_function_code(func)
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
        byte = _six_ord(byte)
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


def _is_descriptor(obj):
    return hasattr(obj, '__get__') or hasattr(obj, '__set__') or hasattr(obj, '__delete__')


def _signature_info(arg_spec):
    # type: (ArgSpec) -> (List[str], int, int, int, bool, bool)
    """ returns (req_args, def_args, has_varargs, has_keywords)"""
    if arg_spec.defaults:
        n_defaults = len(arg_spec.defaults)
        def_args = arg_spec.args[-n_defaults:]
        req_args = arg_spec.args[:-n_defaults]
    else:
        req_args = arg_spec.args
        def_args = []
    return req_args, def_args, bool(arg_spec.varargs), bool(arg_spec.keywords)


def _signatures_are_consistent(func_sig, base_sig):
    """
    :param func_sig: ArgSpec named tuple for overriding function
    :param base_sig: ArgSpec named tuple for base class function
    :return: True if signatures are consistent.
    2 function signatures are consistent if:
        * The argument names match
        * new arguments in func_sig have defaults
    """
    base_required_args, base_default_args, base_varargs, base_keywords = _signature_info(base_sig)
    func_required_args, func_default_args, func_varargs, func_keywords = _signature_info(func_sig)
    if func_varargs:
        shortest_len = min(len(base_required_args), len(func_required_args))
        req_names_match = func_required_args[:shortest_len] == base_required_args[:shortest_len]
    else:
        # (a, b, c) can be overridden with (a, b, c=0) so need to check entire args sequence here
        req_names_match = func_sig.args[:len(base_required_args)] == base_required_args
    no_new_required_args = len(func_required_args) <= len(base_required_args)
    if func_keywords:
        def_names_match = True
    else:
        def_names_match = func_default_args[:len(base_default_args)] == base_default_args
    if base_default_args and func_varargs:
        # need to check that we don't have multiple values for keyword arguments
        # e.g. base(a, b, c=None)  func(a, c=4, *args)
        # base can be called with (a, b, c) but func cannot.
        for arg in func_default_args:
            if arg in base_sig.args:
                base_index = base_sig.args.index(arg)
                func_index = func_sig.args.index(arg)
                if base_index != func_index:
                    def_names_match = False
                    break
    return req_names_match and def_names_match and no_new_required_args


def _ensure_everything_is_abstract(attributes):
    # all methods and properties are abstract on a pure interface
    namespace = {}
    functions = []
    interface_method_signatures = {}
    interface_property_names = set()
    for name, value in six.iteritems(attributes):
        if _builtin_attrs(name):
            pass  # shortcut
        elif getattr(value, '__isabstractmethod__', False):
            if isinstance(value, (staticmethod, classmethod, types.FunctionType)):
                if isinstance(value, (staticmethod, classmethod)):
                    func = value.__func__
                else:
                    func = value
                functions.append(func)
                interface_method_signatures[name] = getargspec(func)
            elif isinstance(value, property):
                interface_property_names.add(name)
        elif isinstance(value, staticmethod):
            func = value.__func__
            functions.append(func)
            interface_method_signatures[name] = getargspec(func)
            value = abstractstaticmethod(func)
        elif isinstance(value, classmethod):
            func = value.__func__
            interface_method_signatures[name] = getargspec(func)
            functions.append(func)
            value = abstractclassmethod(func)
        elif isinstance(value, types.FunctionType):
            functions.append(value)
            interface_method_signatures[name] = getargspec(value)
            value = abstractmethod(value)
        elif isinstance(value, property):
            interface_property_names.add(name)
            functions.extend([value.fget, value.fset, value.fdel])  # may contain Nones
            value = abstractproperty(value.fget, value.fset, value.fdel)
        namespace[name] = value
    return namespace, functions, interface_method_signatures, interface_property_names


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
        func_sig = getargspec(func)
        if not _signatures_are_consistent(func_sig, base_sig):
            msg = '{module}.{clsname}.{name} argments does not match base class'.format(
                module=attributes['__module__'], clsname=clsname, name=name)
            raise InterfaceError(msg)


def _patch_properties(cls, base_abstract_properties):
    """ Create an AttributeProperty for interface properties not provided by an implementation.
    """
    abstract_properties = set()
    functions = []
    for attr in cls.__abstractmethods__:
        value = getattr(cls, attr)
        if isinstance(value, abstractproperty):
            functions.extend([value.fget, value.fset, value.fdel])  # may contain Nones
            setattr(cls, attr, AttributeProperty(attr))
            abstract_properties.add(attr)
    cls._pi.abstractproperties = frozenset(abstract_properties | base_abstract_properties)
    abstractmethods = set(cls.__abstractmethods__) - abstract_properties
    for func in functions:
        if func is not None and func.__name__ in abstractmethods:
            abstractmethods.discard(func.__name__)
    cls.__abstractmethods__ = frozenset(abstractmethods)


class PureInterfaceType(abc.ABCMeta):
    """
    Meta-Class for PureInterface.
    This type:
        * determines if the new class is an interface or a concrete class.
        * if the type is an interface:
            * mark all methods and properties as abstract
            * ensure all method and property bodies are empty
        * optionally check overriding method signatures match those on base class.
        * if the type is a concrete class then patch the abstract properties with AttributeProperies.
    """

    def __new__(mcs, clsname, bases, attributes):
        base_types = [(cls, _type_is_pure_interface(cls)) for cls in bases]
        type_is_interface = all(is_interface for cls, is_interface in base_types)
        if clsname == 'PureInterface' and attributes['__module__'] == 'pure_interface':
            type_is_interface = True
        elif len(bases) > 1 and bases[0] is object:
            bases = bases[1:]  # create a consistent MRO order
            base_types = base_types[1:]
        interface_method_signatures = dict()
        interface_property_names = set()
        base_abstract_properties = set()
        for i in range(len(bases)-1, -1, -1):  # start at back end
            base, base_is_interface = base_types[i]
            if base is object:
                continue
            abstract_properties = _get_pi_attribute(base, 'abstractproperties', set())
            base_abstract_properties.update(abstract_properties)
            if base_is_interface:
                if hasattr(base, '_pi'):
                    method_signatures = _get_pi_attribute(base, 'interface_method_signatures', {})
                    property_names = _get_pi_attribute(base, 'interface_property_names', set())
                else:
                    property_names, method_signatures = _get_abc_interface_props_and_funcs(base)
                interface_method_signatures.update(method_signatures)
                interface_property_names.update(property_names)
            elif not issubclass(base, PureInterface) and IS_DEVELOPMENT:
                _check_method_signatures(base.__dict__, base.__name__, interface_method_signatures)

        if IS_DEVELOPMENT:
            _check_method_signatures(attributes, clsname, interface_method_signatures)

        if type_is_interface:
            namespace, functions, method_signatures, property_names = _ensure_everything_is_abstract(attributes)
            interface_method_signatures.update(method_signatures)
            interface_property_names.update(property_names)
            unwrap = getattr(mcs, '_pi_unwrap_decorators', False)
            for func in functions:
                if func is None:
                    continue
                if not _is_empty_function(func, unwrap):
                    raise InterfaceError('Function "{}" is not empty.\nDid you forget to inherit from object to make the class concrete?'.format(func.__name__))
        else:  # concrete sub-type
            namespace = attributes

        cls = super(PureInterfaceType, mcs).__new__(mcs, clsname, bases, namespace)
        cls._pi = _PIAttributes(type_is_interface, interface_method_signatures, interface_property_names)
        if not type_is_interface:
            class_properties = set(k for k, v in namespace.items() if isinstance(v, property))
            base_abstract_properties.difference_update(class_properties)
            _patch_properties(cls, base_abstract_properties)
            if IS_DEVELOPMENT and cls.__abstractmethods__:
                stacklevel = 2
                stack = inspect.stack()
                while stacklevel < len(stack) and 'pure_interface' in stack[stacklevel][1]:
                    stacklevel += 1
                for method_name in cls.__abstractmethods__:
                    message = 'Incomplete Implementation: {clsname} does not implement {method_name}'
                    message = message.format(clsname=clsname, method_name=method_name)
                    missing_method_warnings.append(message)
                    warnings.warn(message, stacklevel=stacklevel)
        if type_is_interface and not cls.__abstractmethods__:
            cls.__abstractmethods__ = frozenset({''})  # empty interfaces still should not be instantiated
        return cls

    def __call__(cls, *args, **kwargs):
        """ Check that abstract properties are created in constructor """
        if cls._pi.type_is_pure_interface:
            raise TypeError('Interfaces cannot be instantiated')
        self = super(PureInterfaceType, cls).__call__(*args, **kwargs)
        for attr in cls._pi.abstractproperties:
            if not hasattr(self, attr):
                raise TypeError('{}.__init__ does not create required attribute "{}"'.format(cls.__name__, attr))
        return self

    # provided_by duck-type checking
    def _ducktype_check(cls, instance):
        subclass = type(instance)
        for attr in cls._pi.interface_method_names:
            subtype_value = getattr(subclass, attr, None)
            if not callable(subtype_value):
                return False
        for attr in cls._pi.interface_property_names:
            if not hasattr(instance, attr):
                return False
        return True

    def _class_ducktype_check(cls, subclass):
        if subclass in cls._pi.ducktype_subclasses:
            return True

        for attr in cls._pi.interface_method_names:
            subtype_value = getattr(subclass, attr, None)
            if not callable(subtype_value):
                return False
        for attr in cls._pi.interface_property_names:
            if not hasattr(subclass, attr):
                return False

        cls._pi.ducktype_subclasses.add(subclass)
        if IS_DEVELOPMENT:
            stacklevel = 2
            stack = inspect.stack()
            while stacklevel < len(stack) and 'pure_interface' in stack[stacklevel][1]:
                stacklevel += 1
            warnings.warn('Class {module}.{sub_name} implements {cls_name}.\n'
                          'Consider inheriting {cls_name} or using {cls_name}.register({sub_name})'
                          .format(cls_name=cls.__name__, sub_name=subclass.__name__, module=cls.__module__),
                          stacklevel=stacklevel)
        return True

    def provided_by(cls, obj, allow_implicit=True):
        """ Returns True if obj provides this interface.
        provided_by(cls, obj) is equivalent to isinstance(obj, cls) unless allow_implicit is True
        If allow_implicit is True then returns True if interface duck-type check passes.
        Returns False otherwise.
        """
        if not cls._pi.type_is_pure_interface:
            raise ValueError('provided_by() can only be called on interfaces')
        if isinstance(obj, cls):
            return True
        if not allow_implicit:
            return False
        if cls._class_ducktype_check(type(obj)):
            return True
        return cls._ducktype_check(obj)

    def interface_only(cls, implementation):
        """ Returns a wrapper around implementation that provides ONLY this interface. """
        if cls._pi.impl_wrapper_type is None:
            type_name = cls.__name__ + 'Only'
            attributes = {'__module__': cls.__module__}
            cls._pi.impl_wrapper_type = type(type_name, (_ImplementationWrapper,), attributes)
            cls.register(cls._pi.impl_wrapper_type)
        return cls._pi.impl_wrapper_type(implementation, cls)

    def adapt(cls, obj, allow_implicit=False, interface_only=None):
        """ Adapts obj to interface, returning obj if to_interface.provided_by(obj, allow_implicit) is True
        and raising ValueError if no adapter is found
        If interface_only is True, or interface_only is None and IS_DEVELOPMENT is True then the
        returned object is wrapped by an object that only provides the methods and properties defined by to_interface.
        """
        if interface_only is None:
            interface_only = IS_DEVELOPMENT
        if cls.provided_by(obj, allow_implicit=allow_implicit):
            adapted = obj
            if interface_only:
                adapted = cls.interface_only(adapted)
            return adapted

        adapters = cls._pi.adapters
        if not adapters:
            raise ValueError('Cannot adapt {} to {}'.format(obj, cls.__name__))

        for obj_class in type(obj).__mro__:
            if obj_class in adapters:
                factory = adapters[obj_class]
                adapted = factory(obj)
                if not cls.provided_by(adapted, allow_implicit):
                    raise ValueError('Adapter {} does not implement interface {}'.format(factory, cls.__name__))
                if interface_only:
                    adapted = cls.interface_only(adapted)
                return adapted
        raise ValueError('Cannot adapt {} to {}'.format(obj, cls.__name__))

    def adapt_or_none(cls, obj, allow_implicit=False, interface_only=None):
        """ Adapt obj to to_interface or return None if adaption fails """
        try:
            return cls.adapt(obj, allow_implicit=allow_implicit, interface_only=interface_only)
        except ValueError:
            return None

    def can_adapt(cls, obj, allow_implicit=False):
        """ Returns True if adapt(obj, allow_implicit) will succeed."""
        try:
            cls.adapt(obj, allow_implicit=allow_implicit)
        except ValueError:
            return False
        return True

    def filter_adapt(cls, objects, allow_implicit=False, interface_only=None):
        """ Generates adaptions of the given objects to this interface.
        Objects that cannot be adapted to this interface are silently skipped.
        """
        for obj in objects:
            try:
                f = cls.adapt(obj, allow_implicit=allow_implicit, interface_only=interface_only)
            except ValueError:
                continue
            yield f


ABC = abc.ABC if hasattr(abc, 'ABC') else object


@six.add_metaclass(PureInterfaceType)
class PureInterface(ABC):
    pass


# adaption
def adapts(from_type, to_interface=None):
    """Class or function decorator for declaring an adapter from a type to an interface.
    E.g.
        @adapts(MyClass, MyInterface)
        def interface_factory(obj):
            ....

    If decorating a class to_interface may be None to use the first interface in the class's MRO.
    E.g.
        @adapts(MyClass)
        class MyClassToInterfaceAdapter(object, MyInterface):
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
    # types: (from_type) -> to_interface, type, PureInterfaceType
    """ Registers adapter to convert instances of from_type to objects that provide to_interface
    for the to_interface.adapt() method.

    :param adapter: callable that takes an instance of from_type and returns an object providing to_interface.
    :param from_type: a type to adapt from
    :param to_interface: a (non-concrete) PureInterface subclass to adapt to.
    """
    if not callable(adapter):
        raise ValueError('adapter must be callable')
    if not isinstance(from_type, type):
        raise ValueError('{} must be a type'.format(from_type))
    if not (isinstance(to_interface, type) and _get_pi_attribute(to_interface, 'type_is_pure_interface', False)):
        raise ValueError('{} is not an interface'.format(to_interface))
    adapters = _get_pi_attribute(to_interface, 'adapters')
    if from_type in adapters:
        raise ValueError('{} already has an adapter to {}'.format(from_type, to_interface))
    adapters[from_type] = weakref.proxy(adapter)


def type_is_pure_interface(cls):
    """ Return True if cls is a pure interface"""
    try:
        if not issubclass(cls, PureInterface):
            return False
    except TypeError:  # handle non-classes
        return False
    return _get_pi_attribute(cls, 'type_is_pure_interface', False)


def get_type_interfaces(cls):
    """ Returns all interfaces in the cls mro including cls itself if it is an interface """
    try:
        bases = cls.mro()
    except AttributeError:  # handle non-classes
        return []
    return [base for base in bases if type_is_pure_interface(base) and base is not PureInterface]


def get_interface_method_names(interface):
    """ returns a frozen set of names of methods defined by the interface.
    if interface is not a PureInterface subtype then an empty set is returned
    """
    if type_is_pure_interface(interface):
        return _get_pi_attribute(interface, 'interface_method_names')
    else:
        return frozenset()


def get_interface_property_names(interface):
    """ returns a frozen set of names of properties defined by the interface
    if interface is not a PureInterface subtype then an empty set is returned
    """
    if type_is_pure_interface(interface):
        return _get_pi_attribute(interface, 'interface_property_names')
    else:
        return frozenset()
