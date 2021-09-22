pure-interface
==============

A Python interface library that disallows function body content on interfaces and supports adaption.

Jump to the `Reference`_.

Features
--------
* Prevents code in method bodies of an interface class
* Ensures that method overrides have compatible signatures
* Supports interface adaption.
* Supports optional structural type checking for ``Interface.provided_by(a)`` and ``Interface.adapt(a)``
* Allows concrete implementations the flexibility to implement abstract properties as instance attributes.
* ``Interface.adapt()`` can return an implementation wrapper that provides *only* the
  attributes and methods defined by ``Interface``.
* Warns if ``provided_by`` did a structural type check when inheritance would work.
* Supports python 2.7 and 3.5+

A note on the name
------------------
The phrase *pure interface* applies only to the first design goal - a class that defines only an interface with no
implementation is a pure interface [*]_.
In every other respect the zen of 'practicality beats purity' applies.

Installation
------------
You can install released versions of ``pure_interface`` using pip::

    pip install pure-interface

or you can grab the source code from GitHub_.

Defining an Interface
=====================

For simplicity in these examples we assume that the entire pure_interface namespace has been imported ::

    from pure_interface import *

To define an interface, simply inherit from the class ``Interface`` and write a PEP-544_ Protocol-like class
leaving all method bodies empty::

    class IAnimal(Interface):
        height: float

        def speak(self, volume):
            pass


Like Protocols, class annotations are considered part of the interface.
In Python versions earlier than 3.6 you can use the following alternate syntax::

    class IAnimal(Interface):
        height = None

        def speak(self, volume):
            pass

The value assigned to class attributes *must* be ``None`` and the attribute is removed from the class dictionary
(since annotations are not in the class dictionary).

``Interface`` is a subtype of ``abc.ABC`` and the ``abstractmethod``, ``abstractclassmethod`` and ``abstractstaticmethod`` decorators work as expected.
ABC-style property definitions are also supported (and equivalent)::

    class IAnimal(Interface):
        @property
        @abstractmethod
        def height(self):
            pass

        @abstractmethod
        def speak(self, volume):
            pass

Again, the height property is removed from the class dictionary, but, as with the other syntaxes,
all concrete subclasses will be required to have a ``height`` attribute.

For convenience the ``abc`` module abstract decorators are included in the ``pure_interface`` namespace.
However these decorators are optional as **ALL** methods and properties on a ``Interface`` subclass are abstract.
In the examples above, both ``height`` and ``speak`` are considered abstract and must be overridden by subclasses.

Including abstract decorators in your code can be useful for reminding yourself (and telling your IDE) that you need
to override those methods.  Another common way of informing an IDE that a method needs to be overridden is for
the method to raise ``NotImplementedError``.  For this reason methods that just ``raise NotImplementedError`` are also
considered empty.

Interface classes cannot be instantiated ::

    IAnimal()
    InterfaceError: Interfaces cannot be instantiated.

Including code in a method will result in an ``InterfaceError`` being raised when the module is imported. For example::

    class BadInterface(Interface):
        def method(self):
            print('hello')

    InterfaceError: Function "method" is not empty
    Did you forget to inherit from object to make the class concrete?


The ``dir()`` function will include all interface attributes so that ``mock.Mock(spec=IAnimal)`` will work as expected::

    >>> dir(IAnimal)
    ['__abstractmethods__', '__doc__', ..., 'height', 'speak']

The mock_protocol_ package also works well with interfaces.


Concrete Implementations
========================

Simply inheriting from a pure interface and writing a concrete class will result in an ``InterfaceError`` exception
as ``pure_interface`` will assume you are creating a sub-interface. To tell ``pure_interface`` that a type should be
concrete simply inherit from ``object`` as well (or anything else that isn't an ``Interface``).  For example::

    class Animal(IAnimal, object):
        def __init__(self, height):
            self.height = height

        def speak(self, volume):
            print('hello')

**Exception:** Mixing an ``Interface`` class with an ``abc.ABC`` interface class that only defines abstract methods
and properties that satisfy the empty method criteria will result in a type that is considered a pure interface.::

    class ABCInterface(abc.ABC):
        @abstractmethod
        def foo(self):
            pass

    class MyInterface(ABCInterface, Interface):
        def bar(self):
            pass

Concrete implementations may implement interface attributes in any way they like: as instance attributes, properties or
custom descriptors, provided that they all exist at the end of ``__init__()``.  Here is another valid implementation::

    class Animal2(IAnimal, object):
        def __init__(self, height):
            self._height = height

        @property
        def height(self):
            return self._height

        def speak(self, volume):
            print('hello')

Method Signatures
-----------------
Method overrides are checked for compatibility with the interface.
This means that argument names must match exactly and that no new non-optional
arguments are present in the override.  This enforces that calling the method
with interface parameters will aways work.
For example, given the interface method::

  def speak(self, volume):

Then these overrides will all fail the checks and raise an ``InterfaceError``::

   def speak(self):  # too few parameters
   def speak(self, loudness):  # name does not match
   def speak(self, volume, language):  # extra required argument

However new optional parameters are permitted, as are ``*args`` and ``**kwargs``::

  def speak(self, volume, language='doggy speak')
  def speak(self, *args, **kwargs)

Implementation Warnings
-----------------------

As with ``abc.ABC``, the abstract method checking for a class is done when an object is instantiated.
However it is useful to know about missing methods sooner than that.  For this reason ``pure_interface`` will issue
a warning during module import when methods are missing from a concrete subclass.  For example::

    class SilentAnimal(IAnimal, object):
        def __init__(self, height):
            self.height = height

will issue this warning::

    readme.py:28: UserWarning: Incomplete Implementation: SilentAnimal does not implement speak
    class SilentAnimal(IAnimal, object):

Trying to create a ``SilentAnimal`` will fail in the standard abc way::

    SilentAnimal()
    InterfaceError: Can't instantiate abstract class SilentAnimal with abstract methods speak

If you have a mixin class that implements part of an interface you can suppress the warnings by adding an class attribute
called ``pi_partial_implementation``.  The value of the attribute is ignored, and the attribute itself is removed from
the class.  For example::

    class HeightMixin(IAnimal, object):
        pi_partial_implementation = True

        def __init__(self, height):
            self.height = height

will not issue any warnings.

The warning messages are also appended to the module variable ``missing_method_warnings``, irrespective of any warning
module filters (but only if ``is_development=True``).  This provides an alternative to raising warnings as errors.
When all your imports are complete you can check if this list is empty.::

    if pure_iterface.missing_method_warnings:
        for warning in pure_iterface.missing_method_warnings:
            print(warning)
        exit(1)

Note that missing properties are NOT checked for as they may be provided by instance attributes.

Adaption
========

Registering Adapters
--------------------

Adapters for an interface are registered with the ``adapts`` decorator or with
the ``register_adapter`` function. Take for example an interface ``ISpeaker`` and a
class ``Talker`` and an adapter class ``TalkerToSpeaker``::

    class ISpeaker(Interface):
        def speak(self, volume):
            pass

    class Talker(object):
        def talk(self):
            return 'talk'

    @adapts(Talker)
    class TalkerToSpeaker(ISpeaker, object):
        def __init__(self, talker):
            self._talker = talker

        def speak(self, volume):
            return self._talker.talk()

The ``adapts`` decorator call above is equivalent to::

    register_adapter(TalkerToSpeaker, Talker, ISpeaker)

The ``ISpeaker`` parameter passed to ``register_adapter`` is the first interface in the MRO of the class being decorated (``TalkerToSpeaker``).
If there are no interface types in the MRO of the decorated class an ``InterfaceError`` exception is raised.

Adapter factory functions can be decorated too, in which case the interface being adapted to needs to be specified::

    @adapts(Talker, ISpeaker)
    def talker_to_speaker(talker):
        return TalkerToSpeaker(talker)

The decorated adapter (whether class for function) must be callable with a single parameter - the object to adapt.

Adapting Objects
----------------

The ``Interface.adapt`` method will adapt an object to the given interface
such that ``Interface.provided_by`` is ``True`` or raise ``AdaptionError`` if no adapter could be found.  For example::

    speaker = ISpeaker.adapt(talker)
    isinstance(speaker, ISpeaker)  --> True

If you want to get ``None`` rather than an exception then use::

    speaker = ISpeaker.adapt_or_none(talker)

You can filter a list of objects returning those objects that provide an interface
using ``filter_adapt(objects)``::

   list(ISpeaker.filter_adapt([None, Talker(), a_speaker, 'text']) --> [TalkerToSpeaker, a_speaker]

To adapt an object only if it is not ``None`` then use::

    ISpeaker.optional_adapt(optional_talker)

This is equivalent to::

    ISpeaker.adapt(optional_talker) if optional_talker is not None else None

By default the adaption functions will return an object which provides **only**
the functions and properties specified by the interface.  For example given the
following implementation of the ``ISpeaker`` interface above::

  class TopicSpeaker(ISpeaker):
      def __init__(self, topic):
          self.topic = topic

      def speak(self, volume):
          return 'lets talk about {} very {}'.format(self.topic, volume)

  topic_speaker = TopicSpeaker('python')

Then::

  speaker = ISpeaker.adapt(topic_speaker)
  speaker is topic_speaker  --> False
  speaker.topic --> AttributeError("ISpeaker interface has no attribute topic")

This is controlled by the optional ``interface_only`` parameter to ``adapt`` which defaults to ``True``.
Pass ``interface_only=False`` if you want the actual adapted object rather than a wrapper::

  speaker = ISpeaker.adapt(topic_speaker, interface_only=False)
  speaker is topic_speaker  --> True
  speaker.topic --> 'Python'

Accessing the ``topic`` attribute on an ``ISpeaker`` may work for all current implementations
of ``ISpeaker``, but this code will likely break at some inconvenient time in the future.

Adapters from sub-interfaces may be used to perform adaption if necessary. For example::

    class IA(Interface):
       foo = None

    class IB(IA):
        bar = None

    @adapts(int):
    class IntToB(IB, object):
        def __init__(self, x):
            self.foo = self.bar = x

Then  ``IA.adapt(4)`` will use the ``IntToB`` adapter to adapt ``4`` to ``IA`` (unless there is already an adapter
from ``int`` to ``IA``)

Structural Type Checking
========================

Structural_ type checking checks if an object has the attributes and methods defined by the interface.

.. _Structural: https://en.wikipedia.org/wiki/Structural_type_system

As interfaces are inherited, you can usually use ``isinstance(obj, MyInterface)`` to check if an interface is provided.
An alternative to ``isinstance()`` is the ``Interface.provided_by(obj)`` classmethod which will fall back to structural type
checking if the instance is not an actual subclass.  This can be controlled by the ``allow_implicit`` parameter which defaults to ``True``.
The structural type-checking does not check function signatures.::

    class Parrot(object):
        def __init__(self):
            self.height = 43

        def speak(self, volume):
            print('hello')

    p = Parrot()
    isinstance(p, IAnimal) --> False
    IAnimal.provided_by(p) --> True
    IAnimal.provided_by(p, allow_implicit=False) --> False

The structural type checking makes working with data transfer objects (DTO's) much easier.::

    class IMyDataType(Interface):
        thing: str

    class DTO(object):
        pass

    d = DTO()
    d.thing = 'hello'
    IMyDataType.provided_by(d) --> True
    e = DTO()
    e.something_else = True
    IMyDataType.provided_by(e) --> False

Adaption also supports structural typing by passing ``allow_implicit=True`` (but this is not the default)::

    speaker = ISpeaker.adapt(Parrot(), allow_implicit=True)
    ISpeaker.provided_by(speaker)  --> True

When using ``provided_by()`` or ``adapt()`` with ``allow_implicit=True``, a warning may be issued informing you that
the structurally typed object should inherit the interface.  The warning is only issued if the interface is implemented by the
class (and not by instance attributes as in the DTO case above) and the warning is only issued once for each
class, interface pair.  For example::

    s = ISpeaker.adapt(Parrot())
    UserWarning: Class Parrot implements ISpeaker.
    Consider inheriting ISpeaker or using ISpeaker.register(Parrot)

Dataclass Support
=================
dataclasses_ were added in Python 3.7.  When used in this and later versions of Python, ``pure_interface`` provides a
``dataclass`` decorator.  This decorator can be used to create a dataclass that implements an interface.  For example::

    class IAnimal2(Interface):
        height: float
        species: str

        def speak(self):
            pass

    @dataclass
    class Animal(Concrete, IAnimal2):
        def speak(self):
            print('Hello, I am a {} metre tall {}', self.height, self.species)

    a = Animal(height=4.5, species='Giraffe')

The builtin Python ``dataclass`` decorator cannot be used because it will not create attributes for the
``height`` and ``species`` annotations on the interface base class ``IAnimal2``.
As per the built-in ``dataclass`` decorator, only interface attributes defined
using annotation syntax are supported (and not the alternatives syntaxes provided by ``pure_interface``).

Interface Type Information
==========================
The ``pure_interface`` module provides these functions for returning information about interface types.

type_is_interface(cls)
    Return True if cls is a pure interface, False otherwise or if cls is not a class.

get_type_interfaces(cls)
    Returns all interfaces in the cls mro including cls itself if it is an interface

get_interface_names(cls)
    Returns a ``frozenset`` of names (methods and attributes) defined by the interface.
    if interface is not a ``Interface`` subtype then an empty set is returned.

get_interface_method_names(interface)
    Returns a ``frozenset`` of names of methods defined by the interface.
    if interface is not a ``Interface`` subtype then an empty set is returned

get_interface_attribute_names(interface)
    Returns a ``frozenset`` of names of attributes defined by the interface.
    if interface is not a ``Interface`` subtype then an empty set is returned


Automatic Adaption
==================
The function decorator ``adapt_args`` adapts arguments to a decorated function to the types given.
For example::

    @adapt_args(foo=IFoo, bar=IBar)
    def my_func(foo, bar=None):
        pass

In Python 3.5 and later the types can be taken from the argument annotations.::

    @adapt_args
    def my_func(foo: IFoo, bar: IBar=None):
        pass

This would adapt the ``foo`` parameter to ``IFoo`` (with ``IFoo.optional_adapt(foo))`` and ``bar`` to ``IBar
(using ``IBar.optional_adapt(bar)``)
before passing them to my_func.  ``None`` values are never adapted, so ``my_func(foo, None)`` will work, otherwise
``AdaptionError`` is raised if the parameter is not adaptable.
All arguments must be specified as keyword arguments::

    @adapt_args(IFoo, IBar)   # NOT ALLOWED
    def other_func(foo, bar):
        pass

Development Flag
================

Much of the empty function and other checking is awesome whilst writing your code but
ultimately slows down production code.
For this reason the ``pure_interface`` module has an ``is_development`` switch.::

    is_development = not hasattr(sys, 'frozen')

``is_development`` defaults to ``True`` if running from source and default to ``False`` if bundled into an executable by
py2exe_, cx_Freeze_ or similar tools.

If you manually change this flag it must be set before modules using the ``Interface`` type
are imported or else the change will not have any effect.

If ``is_development`` if ``False`` then:

    * Signatures of overriding methods are not checked
    * No warnings are issued by the adaption functions
    * No incomplete implementation warnings are issued
    * The default value of ``interface_only`` is set to ``False``, so that interface wrappers are not created.


PyContracts Integration
=======================

You can use ``pure_interface`` with PyContracts_

.. _PyContracts: https://pypi.python.org/pypi/PyContracts

Simply import the ``pure_contracts`` module and use the ``ContractInterface`` class defined there as you
would the ``Interface`` class described above.
For example::

    from pure_contracts import ContractInterface
    from contracts import contract

    class ISpeaker(ContractInterface):
        @contract(volume=int, returns=unicode)
        def speak(self, volume):
            pass


Reference
=========
Classes
-------

**InterfaceType(abc.ABCMeta)**
    Metaclass for checking interface and implementation classes.
    Adding ``InterfaceType`` as a meta-class to a class will not make that class an interface, you need to
    inherit from ``Interface`` class to define an interface.

    In addition to the ``register`` method provided by ``ABCMeta``, the following functions are defined on
    ``InterfaceType`` and can be accessed directly when the ``Interface`` methods are overridden
    for other purposes.

    **adapt** *(cls, obj, allow_implicit=False, interface_only=None)*
        See ``Interface.adapt`` for a description.

    **adapt_or_none** *(cls, obj, allow_implicit=False, interface_only=None)*
        See ``Interface.adapt_or_none`` for a description

    **optional_adapt** *(cls, obj, allow_implicit=False, interface_only=None)*
        See ``Interface.optional_adapt`` for a description

    **can_adapt** *(cls, obj, allow_implicit=False)*
        See ``Interface.can_adapt`` for a description

    **filter_adapt** *(cls, objects, allow_implicit=False, interface_only=None)*
        See ``Interface.filter_adapt`` for a description

    **interface_only** *(cls, implementation)*
        See ``Interface.interface_only`` for a description

    **provided_by** *(cls, obj, allow_implicit=True)*
        See ``Interface.provided_by`` for a description

    Classes created with a metaclass of ``InterfaceType`` will have the following property:

    **_pi** Information about the class that is used by this meta-class.  This attribute is reserved for use by
            ``pure_interface`` and must not be overridden.


**Interface**
    Base class for defining interfaces.  The following methods are provided:

    **adapt** *(obj, allow_implicit=False, interface_only=None)*
        Adapts ``obj`` to this interface. If ``allow_implicit`` is ``True`` permit structural adaptions.
        If ``interface_only`` is ``None`` the it is set to the value of ``is_development``.
        If ``interface_only`` resolves to ``True`` a wrapper object that provides
        the properties and methods defined by the interface and nothing else is returned.
        Raises ``AdaptionError`` if no adaption is possible or a registered adapter returns an object not providing
        this interface.

    **adapt_or_none** *(obj, allow_implicit=False, interface_only=None)*
        As per **adapt()** except returns ``None`` instead of raising a ``AdaptionError``

    **optional_adapt** *(obj, allow_implicit=False, interface_only=None)*
        Adapts obj to this interface if it is not ``None`` returning ``None`` otherwise.
        Short-cut for ``adapt(obj) if obj is not None else None``

    **can_adapt** *(obj, allow_implicit=False)*
        Returns ``True`` if ``adapt(obj, allow_implicit)`` will succeed.  Short-cut for
        ``adapt_or_none(obj) is not None``

    **filter_adapt** *(objects, allow_implicit=False, interface_only=None)*
        Generates adaptions of each item in *objects* that provide this interface.
        *allow_implicit* and *interface_only* are as for **adapt**.
        Objects that cannot be adapted to this interface are silently skipped.

    **interface_only** *(implementation)*
        Returns a wrapper around *implementation* that provides the properties and methods defined by
        the interface and nothing else.

    **provided_by** *(obj, allow_implicit=True)*
        Returns ``True`` if *obj* provides this interface. If ``allow_implicit`` is ``True`` the also
        return ``True`` for objects that provide the interface structure but do not inherit from it.
        Raises ``InterfaceError`` if the class is a concrete type.

Functions
---------
**adapts** *(from_type, to_interface=None)*
    Class or function decorator for declaring an adapter from *from_type* to *to_interface*.
    The class or function being decorated must take a single argument (an instance of *from_type*) and
    provide (or return and object providing) *to_interface*.  The adapter may return an object that provides
    the interface structurally only, however ``adapt`` must be called with ``allow_implicit=True`` for this to work.
    If decorating a class, *to_interface* may be ``None`` to use the first interface in the class's MRO.

**register_adapter** *(adapter, from_type, to_interface)*
    Registers an adapter to convert instances of *from_type* to objects that provide *to_interface*
    for the *to_interface.adapt()* method. *adapter* must be a callable that takes a single argument
    (an instance of *from_type*) and returns and object providing *to_interface*.

**type_is_interface** *(cls)*
    Return ``True`` if *cls* is a pure interface and ``False`` otherwise

**get_type_interfaces** *(cls)*
    Returns all interfaces in the *cls* mro including cls itself if it is an interface

**get_interface_names** *(cls)*
    Returns a ``frozenset`` of names (methods and attributes) defined by the interface.
    if interface is not a ``Interface`` subtype then an empty set is returned.

**get_interface_method_names** *(cls)*
    Returns a ``frozenset`` of names of methods defined by the interface.
    If *cls* is not a ``Interface`` subtype then an empty set is returned.

**get_interface_attribute_names** *(cls)*
    Returns a ``frozenset`` of names of class attributes and annotations defined by the interface
    If *cls* is not a ``Interface`` subtype then an empty set is returned.

**dataclass** *(_cls=None, init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)*
    This function is a re-implementation of the standard Python ``dataclasses.dataclass`` decorator.
    In addition to the fields on the decorated class, all annotations on interface base classes are added as fields.
    See the Python dataclasses_ documentation for more details.

    3.7+ Only


Exceptions
----------
**PureInterfaceError**
    Base exception class for all exceptions raised by ``pure_interface``.

**InterfaceError**
    Exception raised for problems with interfaces

**AdaptionError**
    Exception raised for problems with adapters or adapting.


Module Attributes
-----------------
**is_development**
    Set to ``True`` to enable all checks and warnings.
    If set to ``False`` then:

    * Signatures of overriding methods are not checked
    * No warnings are issued by the adaption functions
    * No incomplete implementation warnings are issued
    * The default value of ``interface_only`` is set to ``False``, so that interface wrappers are not created.


**missing_method_warnings**
    The list of warning messages for concrete classes with missing interface (abstract) method overrides.
    Note that missing properties are NOT checked for as they may be provided by instance attributes.

-----------

.. _typing: https://pypi.python.org/pypi/typing
.. _PEP-544: https://www.python.org/dev/peps/pep-0544/
.. _GitHub: https://github.com/seequent/pure_interface
.. _mypy: http://mypy-lang.org/
.. _py2exe: https://pypi.python.org/pypi/py2exe
.. _cx_Freeze: https://pypi.python.org/pypi/cx_Freeze
.. _dataclasses: https://docs.python.org/3/library/dataclasses.html
.. _mock_protocol: https://pypi.org/project/mock-protocol/
.. [*] We don't talk about the methods on the base ``Interface`` class.  In earlier versions they
   were all on the meta class but then practicality got in the way.
