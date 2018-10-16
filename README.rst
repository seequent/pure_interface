pure_interface
==============

.. image:: https://travis-ci.com/seequent/pure_interface.svg?branch=master
    :target: https://travis-ci.com/seequent/pure_interface

A Python interface library that disallows function body content on interfaces and supports adaption.

Jump to the `Reference`_.

Features
--------
* Prevents code in method bodies of an interface class
* Ensures that method overrides have compatible signatures
* Supports interface adaption.
* Supports optional structural type checking for ``Interface.provided_by(a)`` and ``Interface.adapt(a)``
* Allows concrete implementations the flexibility to implement abstract properties as instance attributes.
* Treats abc interfaces that do not include any implementation as a pure interface type.
  This means that ``class C(PureInterface, ABCInterface)`` will be a pure interface if the abc interface meets the
  no function body content criteria.
* Warns if ``provided_by`` did a structural type check when inheritance would work.
* Supports python 2.7 and 3.5+

A note on the name
------------------
The phrase *pure interface* applies only to the first design goal - a class that defines only an interface with no
implementation is a pure interface.  In every other respect the zen of 'practicality beats purity' applies.

Installation
------------
pure_interface depends on the six_ and typing_ modules (typing is included in python 3.5 and later).

You can install released versions of ``pure_interface`` using pip::

    pip install pure_interface

or you can grab the source code from GitHub_.

Defining a Pure Interface
=========================

For simplicity in these examples we assume that the entire pure_interface namespace has been imported ::

    from pure_interface import *

To define an interface, simply inherit from the class ``PureInterface`` and write a PEP-544_ Protocol-like class
leaving all method bodies empty::

    class IAnimal(PureInterface):
        height: float

        def speak(self, volume):
            pass


Like Protocols, class annotations are considered part of the interface. In Python versions earlier than 3.6 you can use
the following alternate syntax::

    class IAnimal(PureInterface):
        height = None

        def speak(self, volume):
            pass

The value assigned to class attributes *must* be ``None`` and the attribute is removed from the class dictionary
(since annotations are not in the class dictionary).

``PureInterface`` is a subtype of ``abc.ABC`` and the ``abstractmethod`` and ``abstractproperty`` decorators work as expected.
ABC-style property definitions are also supported (and equivalent)::

    class IAnimal(PureInterface):
        @abstractproperty
        def height(self):
            pass

        def speak(self, volume):
            pass

Again, the height property is removed from the class dictionary, but, as with the other syntaxes,
all concrete subclasses will be required to have a ``height`` attribute.

For convenience the ``abc`` module abstract decorators are included in the ``pure_interface`` namespace, and
on Python 2.7 ``abstractclassmethod`` and ``abstractstaticmethod`` are also available.
However these decorators are optional as **ALL** methods and properties on a ``PureInterface`` subclass are abstract.
In the examples above, both ``height`` and ``speak`` are considered abstract and must be overridden by subclasses.

Including abstract decorators in your code can be useful for reminding yourself (and telling your IDE) that you need
to override those methods.  Another common way of informing an IDE that a method needs to be overridden is for
the method to raise ``NotImplementedError``.  For this reason methods that just raise ``NotImplementedError`` are also
considered empty.

Interface classes cannot be instantiated ::

    IAnimal()
    TypeError: Interfaces cannot be instantiated.

Including code in a method will result in an ``InterfaceError`` being raised when the module is imported. For example::

    class BadInterface(PureInterface):
        def method(self):
            print('hello')

    InterfaceError: Function "method" is not empty
    Did you forget to inherit from object to make the class concrete?


The ``dir()`` function will include all interface attributes so that ``mock.Mock(spec=IAnimal)`` will work as expected::

    >>> dir(IAnimal)
    ['__abstractmethods__', '__doc__', ..., 'height', 'speak']



Concrete Implementations
========================

Simply inheriting from a pure interface and writing a concrete class will result in an ``InterfaceError`` exception
as ``pure_interface`` will assume you are creating a sub-interface. To tell ``pure_interface`` that a type should be
concrete simply inherit from ``object`` as well (or anything else that isn't a ``PureInterface``).  For example::

    class Animal(object, IAnimal):
        def __init__(self, height):
            self.height = height

        def speak(self, volume):
            print('hello')

**Exception:** Mixing a ``PureInterface`` class with an ``abc.ABC`` interface class that only defines abstract methods
and properties that satisfy the empty method criteria will result in a type that is considered a pure interface.::

    class ABCInterface(abc.ABC):
        @abstractmethod
        def foo(self):
            pass

    class MyPureInterface(ABCInterface, PureInterface):
        def bar(self):
            pass

Concrete implementations may implement interface attributes in any way they like: as instance attributes, properties,
custom descriptors provided that they all exist at the end of ``__init__()``.  Here is another valid implementation::

    class Animal2(object, IAnimal):
        def __init__(self, height):
            self._height = height

        @property
        def height(self):
            return self._height

        def speak(self, volume):
            print('hello')

The astute reader will notice that the ``Animal2`` bases list makes an inconsistent method resolution order.
This is handled by the ``PureInterfaceType`` meta-class by removing ``object`` from the front of the bases list.
However static checkers such as mypy_ and some IDE's will complain.  To get around this, ``pure_interface`` includes an empty
``Concrete`` class which you can use to keep mypy and your IDE happy::

    class Concrete(object):
        pass

    class Animal2(Concrete, IAnimal):
        def __init__(self, height):
            self.height = height

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
  def speak(self, *args)

Implementation Warnings
-----------------------

As with ``abc.ABC``, the abstract method checking for a class is done when an object is instantiated.
However it is useful to know about missing methods sooner than that.  For this reason ``pure_interface`` will issue
a warning during module import when methods are missing from a concrete subclass.  For example::

    class SilentAnimal(object, IAnimal):
        def __init__(self, height):
            self.height = height

will issue this warning::

    readme.py:28: UserWarning: Incomplete Implementation: SilentAnimal does not implement speak
    class SilentAnimal(object, IAnimal):

Trying to create a ``SilentAnimal`` will fail in the standard abc way::

    SilentAnimal()
    TypeError: Can't instantiate abstract class SilentAnimal with abstract methods speak

If you have a mixin class that implements part of an interface you can suppress the warnings by adding an class attribute
called ``pi_partial_implementation``.  The value of the attribute is ignored, and the attribute itself is removed from
the class.  For example::

    class HeightMixin(object, IAnimal):
        pi_partial_implementation = True

        def __init__(self, height):
            self.height = height

will not issue any warnings.

The warning messages are also appended to the module variable ``missing_method_warnings``, irrespective of any warning
filters (but only if ``is_development=True``).  This provides an alternative to raising warnings as errors.
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

    class ISpeaker(PureInterface):
        def speak(self, volume):
            pass

    class Talker(object):
        def talk(self):
            return 'talk'

    @adapts(Talker)
    class TalkerToSpeaker(object, ISpeaker):
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

The ``PureInterface.adapt`` method will adapt an object to the given interface
such that ``Interface.provided_by`` is ``True`` or raise ``ValueError`` if no adapter could be found.  For example::

    speaker = ISpeaker.adapt(talker)
    isinstance(speaker, ISpeaker)  --> True

If you want to get ``None`` rather than an exception then use::

    speaker = ISpeaker.adapt_or_none(talker)

You can filter a list of objects returning those objects that provide an interface
using ``filter_adapt(objects)``::

   list(ISpeaker.filter_adapt([None, Talker(), a_speaker, 'text']) --> [TalkerToSpeaker, a_speaker]

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

    class IA(PureInterface):
       foo = None

    class IB(IA):
        bar = None

    @adapts(int):
    class IntToB(object, IB):
        def __init__(self, x):
            self.foo = self.bar = x

Then  ``IA.adapt(4)`` will use the ``IntToB`` adapter to adapt ``4`` to ``IA`` (unless there is already an adapter
from ``int`` to ``IA``)

Structural Type Checking
========================

Structural_ type checking checks if an object has the attributes and methods defined by the interface.

.. _Structural: https://en.wikipedia.org/wiki/Structural_type_system

As interfaces are inherited, you can usually use ``isinstance(obj, MyInterface)`` to check if an interface is provided.
An alternative to ``isinstance()`` is the ``PureInterface.provided_by(obj)`` classmethod which will fall back to structural type
checking if the instance is not an actual subclass.  This can be controlled by the ``allow_implicit`` parameter which defaults to ``True``.
The structural type-checking does not check function signatures.::

    class Parrot(object):
        def __init__(self):
            self._height = 43

        @property
        def height(self):
            return self._height

        def speak(self, volume):
            print('hello')

    p = Parrot()
    isinstance(p, IAnimal) --> False
    IAnimal.provided_by(p) --> True
    IAnimal.provided_by(p, allow_implicit=False) --> False

The structural type checking makes working with data transfer objects (DTO's) much easier.::

    class IMyDataType(PureInterface):
        @property
        def thing(self):
            pass

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

Interface Type Information
==========================
The ``pure_interface`` module provides 4 functions for returning information about interface types.

type_is_pure_interface(cls)
    Return True if cls is a pure interface, False otherwise or if cls is not a class.

get_type_interfaces(cls)
    Returns all interfaces in the cls mro including cls itself if it is an interface

get_interface_method_names(interface)
    Returns a frozen set of names of methods defined by the interface.
    if interface is not a ``PureInterface`` subtype then an empty set is returned

get_interface_attribute_names(interface)
    Returns a frozen set of names of attributes defined by the interface.
    if interface is not a ``PureInterface`` subtype then an empty set is returned


Development Flag
================

Much of the empty function and other checking is awesome whilst writing your code but
ultimately slows down production code.
For this reason the ``pure_interface`` module has an ``is_development`` switch.::

    is_development = not hasattr(sys, 'frozen')

``is_development`` defaults to ``True`` if running from source and default to ``False`` if bundled into an executable by
py2exe_, cx_Freeze_ or similar tools.

If you manually change this flag it must be set before modules using the ``PureInterface`` type
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
would the ``PureInterface`` class described above.
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

**PureInterfaceType**
    Metaclass for checking interface and implementation classes.
    Adding PureInterfaceType as a meta-class to a class will not make that class an interface, you need to
    inherit from ``PureInterface`` class to define an interface.

    Classes created with a metaclass of ``PureInterfaceType`` will have the following property:

    **_pi** Information about the class that is used by this meta-class


**PureInterface**
    Base class for defining interfaces.  The following methods are provided:

    **adapt** *(obj, allow_implicit=False, interface_only=None)*
        Adapts ``obj`` to this interface. If ``allow_implicit`` is ``True`` permit structural adaptions.
        If ``interface_only`` is ``None`` the it is set to the value of ``is_development``.
        If ``interface_only`` resolves to ``True`` a wrapper object that provides
        the properties and methods defined by the interface and nothing else is returned.
        Raises ``ValueError`` if no adaption is possible or a registered adapter returns an object not providing
        this interface.

    **adapt_or_none** *(obj, allow_implicit=False, interface_only=None)*
        As per **adapt()** except returns ``None`` instead of raising a ``ValueError``

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
        Raises ``ValueError`` if the class is a concrete type.


**Concrete**
    Empty class to create a consistent MRO in implementation classes.


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

**type_is_pure_interface** *(cls)*
    Return ``True`` if *cls* is a pure interface and ``False`` otherwise

**get_type_interfaces** *(cls)*
    Returns all interfaces in the *cls* mro including cls itself if it is an interface

**get_interface_method_names** *(cls)*
    Returns a ``frozenset`` of names of methods defined by the interface.
    If *cls* is not a interface type then an empty set is returned.

**get_interface_attribute_names** *(cls)*
    Returns a ``frozenset`` of names of class attributes and annotations defined by the interface
    If *cls* is not a interface type then an empty set is returned.


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


.. _six: https://pypi.python.org/pypi/six
.. _typing: https://pypi.python.org/pypi/typing
.. _PEP-544: https://www.python.org/dev/peps/pep-0544/
.. _GitHub: https://github.com/aranzgeo/pure_interface
.. _mypy: http://mypy-lang.org/
.. _py2exe: https://pypi.python.org/pypi/py2exe
.. _cx_Freeze: https://pypi.python.org/pypi/cx_Freeze

