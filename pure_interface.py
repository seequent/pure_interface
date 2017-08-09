try:
    from abc import abstractmethod, abstractproperty, abstractclassmethod, abstractstaticmethod
except ImportError:
    from abc import abstractmethod, abstractproperty


    class abstractclassmethod(classmethod):
        __isabstractmethod__ = True

        def __init__(self, callable):
            self.im_func = callable
            callable.__isabstractmethod__ = True
            super(abstractclassmethod, self).__init__(callable)


    class abstractstaticmethod(staticmethod):
        __isabstractmethod__ = True

        def __init__(self, callable):
            self.im_func = callable
            callable.__isabstractmethod__ = True
            super(abstractstaticmethod, self).__init__(callable)

import abc
import dis
import types
import sys
import warnings
import weakref

import six

__version__ = '1.7.0'


IS_DEVELOPMENT = not hasattr(sys, 'frozen')

if six.PY2:
    _six_ord = ord
else:
    _six_ord = lambda x: x


class InterfaceError(Exception):
    pass


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


class DelegateProperty(object):
    def __init__(self, impl, name):
        self.impl = impl
        self.name = name
        super(DelegateProperty, self).__init__()

    def __get__(self, instance, owner):
        if instance is None:
            return getattr(type(self.impl), self.name)
        return getattr(self.impl, self.name)

    def __set__(self, instance, value):
        setattr(self.impl, self.name, value)


class _ImplementationWrapper(object):
    def __init__(self, implementation, interface):
        self.__impl = implementation
        self.__interface = interface
        self.__method_names = interface._pi_interface_method_names
        self.__property_names = interface._pi_interface_property_names
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
                    '_abc_cache', '_abc_registry', '_abc_negative_cache_version', '_abc_negative_cache')


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
        byte = _six_ord(byte)
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
        return False # return is not None
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

    return False


def _get_function_signature(function):
    """ Returns a list of argument names and the number of default arguments """
    code_obj = function.__code__
    args = code_obj.co_varnames[:code_obj.co_argcount]
    return args, len(function.__defaults__) if function.__defaults__ is not None else 0


def _signatures_are_consistent(func_sig, base_sig):
    """
    :param func_sig: (args, num_default) tuple for overriding function
    :param base_sig: (args, num_default) tuple for base class function
    :return: True if signatures are consistent.
    2 function signatures are consistent if:
        * The argument names match
        * new arguments in func_sig have defaults
        * The number of arguments without defaults does not increase
    """
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
    """ Return True if func does not override an existing method.
    Also return True if there is a method the signatures are consistent """
    func_sig = _get_function_signature(func)
    for base in bases:
        if base is object:
            continue
        if name in base.__dict__:
            base_func = getattr(base, name)
            if hasattr(base_func, six._meth_func):
                base_func = six.get_method_function(base_func)
            base_sig = _get_function_signature(base_func)
            return _signatures_are_consistent(func_sig, base_sig)
    return True


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
    _pi_unwrap_decorators = False

    def __new__(mcs, clsname, bases, attributes):
        base_types = [(cls, _type_is_pure_interface(cls)) for cls in bases]
        type_is_interface = all(is_interface for cls, is_interface in base_types)
        if clsname == 'PureInterface' and attributes['__module__'] == 'pure_interface':
            type_is_interface = True
        elif bases[0] is object:
            bases = bases[1:]  # create a consistent MRO order
        interface_method_names = set()
        interface_property_names = set()
        bases_to_check = []
        for base, base_is_interface in base_types:
            if base is object:
                continue
            if base_is_interface:
                base_interface_method_names = getattr(base, '_pi_interface_method_names', set())
                interface_method_names.update(base_interface_method_names)
                base_interface_property_names = getattr(base, '_pi_interface_property_names', set())
                interface_property_names.update(base_interface_property_names)
            elif not isinstance(base, PureInterfaceType):
                bases_to_check.append(base)
        if type_is_interface:
            namespace, functions, method_names, property_names = mcs._ensure_everything_is_abstract(attributes)
            interface_method_names.update(method_names)
            interface_property_names.update(property_names)
            for func in functions:
                if func is not None and not _is_empty_function(func, mcs._pi_unwrap_decorators):
                    raise InterfaceError('Function "{}" is not empty'.format(func.__name__))
        else:  # concrete sub-type
            namespace = attributes
        if IS_DEVELOPMENT and _ImplementationWrapper not in bases:
            mcs._check_method_signatures(attributes, bases, clsname, interface_method_names)
            for base in bases_to_check:
                i = bases.index(base)
                mcs._check_method_signatures(base.__dict__, bases[i+1:], clsname, interface_method_names)

        cls = super(PureInterfaceType, mcs).__new__(mcs, clsname, bases, namespace)
        cls._pi_type_is_pure_interface = type_is_interface
        cls._pi_abstractproperties = frozenset()
        cls._pi_interface_method_names = frozenset(interface_method_names)
        cls._pi_interface_property_names = frozenset(interface_property_names)
        cls._pi_adapters = weakref.WeakKeyDictionary()
        cls._pi_ducktype_subclasses = set()
        cls._pi_impl_wrapper_type = None
        if not type_is_interface:
            mcs._patch_properties(cls)
        if type_is_interface and not cls.__abstractmethods__:
            cls.__abstractmethods__ = frozenset({''})  # empty interfaces still should not be instantiated
        return cls

    @staticmethod
    def _patch_properties(cls):
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

    @staticmethod
    def _check_method_signatures(attributes, bases, clsname, interface_method_names):
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

    @staticmethod
    def _ensure_everything_is_abstract(attributes):
        # all methods and properties are abstract
        namespace = {}
        functions = []
        interface_method_names = set()
        interface_property_names = set()
        for name, value in six.iteritems(attributes):
            if _builtin_attrs(name):
                pass  # shortcut
            elif getattr(value, '__isabstractmethod__', False):
                if isinstance(value, (staticmethod, classmethod, types.FunctionType)):
                    interface_method_names.add(name)
                    if isinstance(value, (staticmethod, classmethod)):
                        func = six.get_method_function(value)
                    else:
                        func = value
                    functions.append(func)
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
            namespace[name] = value
        return namespace, functions, interface_method_names, interface_property_names

    def __call__(cls, *args, **kwargs):
        """ Check that abstract properties are created in constructor """
        self = super(PureInterfaceType, cls).__call__(*args, **kwargs)
        for attr in cls._pi_abstractproperties:
            if not hasattr(self, attr):
                raise TypeError('__init__ does not create required attribute "{}"'.format(attr))
        return self

    # provided_by duck-type checking
    def _ducktype_check(cls, instance):
        subclass = type(instance)
        for attr in cls._pi_interface_method_names:
            subtype_value = getattr(subclass, attr, None)
            if not callable(subtype_value):
                return False
        for attr in cls._pi_interface_property_names:
            if not hasattr(instance, attr):
                return False
        return True

    def _class_ducktype_check(cls, subclass):
        if subclass in cls._pi_ducktype_subclasses:
            return True

        for attr in cls._pi_interface_method_names:
            subtype_value = getattr(subclass, attr, None)
            if not callable(subtype_value):
                return False
        for attr in cls._pi_interface_property_names:
            if not hasattr(subclass, attr):
                return False

        cls._pi_ducktype_subclasses.add(subclass)
        if IS_DEVELOPMENT:
            stacklevel = 2
            warnings.warn('Class {module}.{sub_name} implements {cls_name}.\n'
                          'Consider inheriting {cls_name} or using {cls_name}.register({sub_name})'
                          .format(cls_name=cls.__name__, sub_name=subclass.__name__, module=cls.__module__),
                          stacklevel=stacklevel)
        return True

    def provided_by(cls, obj):
        # (Any) -> bool
        """ Returns True if obj provides this interface, either by inheritance or duck-typing.  False otherwise """
        if not cls._pi_type_is_pure_interface:
            raise ValueError('provided_by() can only be called on interfaces')
        if isinstance(obj, cls):
            return True
        if cls._class_ducktype_check(type(obj)):
            return True
        return cls._ducktype_check(obj)

    def interface_only(cls, implementation):
        """ Returns a wrapper around implementation that provides ONLY this interface. """
        if cls._pi_impl_wrapper_type is None:
            type_name = cls.__name__ + 'Only'
            attributes = {name: DelegateProperty(implementation, name)
                          for name in list(cls._pi_interface_method_names) + list(cls._pi_interface_property_names)}
            attributes['__module__'] = cls.__module__
            cls._pi_impl_wrapper_type = type(type_name, (_ImplementationWrapper, cls), attributes)
        return cls._pi_impl_wrapper_type(implementation, cls)

    def adapt(cls, obj, interface_only=None):
        """ Adapts obj to interface, returning obj if to_interface.provided_by(obj) is True
        and raising ValueError if no adapter is found
        If interface_only is True, obj is wrapped by an object that only provides the methods and properties
        defined by to_interface.
        """
        if interface_only is None:
            interface_only = IS_DEVELOPMENT
        if cls.provided_by(obj):
            adapted = obj
            if interface_only:
                adapted = cls.interface_only(adapted)
            return adapted

        adapters = cls._pi_adapters
        if not adapters:
            raise ValueError('Cannot adapt {} to {}'.format(obj, cls.__name__))

        for obj_class in type(obj).__mro__:
            if obj_class in adapters:
                factory = adapters[obj_class]
                adapted = factory(obj)
                if not cls.provided_by(adapted):
                    raise ValueError('Adapter {} does not implement interface {}'.format(factory, cls.__name__))
                if interface_only:
                    adapted = cls.interface_only(adapted)
                return adapted
        raise ValueError('Cannot adapt {} to {}'.format(obj, cls.__name__))

    def adapt_or_none(cls, obj, interface_only=None):
        """ Returns True if obj provides this interface, either by inheritance or duck-typing.  False otherwise """
        """ Adapt obj to to_interface or return None if adaption fails """
        try:
            return cls.adapt(obj, interface_only=interface_only)
        except ValueError:
            return None

    def filter_adapt(cls, objects, interface_only=None):
        """ Generates adaptions of the given objects to this interface.
        Objects that cannot be adapted to this interface are silently skipped.
        """
        for obj in objects:
            f = cls.adapt_or_none(obj, interface_only=interface_only)
            if f is not None:
                yield f


@six.add_metaclass(PureInterfaceType)
class PureInterface(abc.ABC if hasattr(abc, 'ABC') else object):
    pass


# adaption
def adapts(from_type, to_interface):
    """Class or function decorator for declaring an adapter from a type to an interface.
    E.g.
        @adapts(MyClass, Interface)
        class MyClassToInterfaceAdapter(object):
            def __init__(self, obj):
                ....
    """

    def decorator(cls):
        register_adapter(cls, from_type, to_interface)
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
    if isinstance(None, from_type):
        raise ValueError('Cannot adapt None type')
    if not (isinstance(to_interface, type) and getattr(to_interface, '_pi_type_is_pure_interface', False)):
        raise ValueError('{} is not an interface'.format(to_interface))
    if from_type in to_interface._pi_adapters:
        raise ValueError('{} already has an adapter to {}'.format(from_type, to_interface))
    to_interface._pi_adapters[from_type] = weakref.proxy(adapter)
