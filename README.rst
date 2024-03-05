pure_interface
==============

A Python interface library that disallows function body content on interfaces and supports adaption.

Jump to the `Reference`_.

Features
--------
* Prevents code in method bodies of an interface class
* Ensures that method overrides have compatible signatures
* Supports interface adaption.
* Supports optional structural type checking.
* Allows concrete implementations the flexibility to implement abstract properties as instance attributes.
* ``Interface.adapt()`` can return an implementation wrapper that provides *only* the
  attributes and methods defined by ``Interface``.
* Supports python 3.8+

**A note on the name**

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

For simplicity in these examples we assume that the entire ``pure_interface`` namespace has been imported ::

    from pure_interface import *

To define an interface, simply inherit from the class ``Interface`` and write a PEP-544_ Protocol-like class
leaving all method bodies empty::

    class IAnimal(Interface):
        height: float

        def speak(self):
            pass


Like Protocols, class annotations are considered part of the interface.
For historical reasons, you can also use the following alternate syntax::

    class IAnimal(Interface):
        height = None

        def speak(self):
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
        def speak(self):
            pass

Again, the height property is removed from the class dictionary, but, as with the other syntaxes,
all concrete subclasses will be required to have a ``height`` attribute.

Note that the ``abstractmethod`` decorator is optional as **ALL** methods and properties on a ``Interface`` subclass are abstract.
All the examples above are equivalent, both ``height`` and ``speak`` are considered abstract and must be overridden by subclasses.

Including ``abstractmethod`` decorators in your code can be useful for reminding yourself (and telling your IDE) that you need
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

Mixing ``Interface`` with non-interface types in a bases list will raise an ``InterfaceError`` at module load time.
There are two exceptions to this rule. `typing.Generic` is permitted as well as empty ``abc.ABC`` classes
that only defines abstract methods
and properties that satisfy the empty method criteria will result in a type that is considered a pure interface.::

    class ABCInterface(abc.ABC):
        @abstractmethod
        def foo(self):
            pass

    class MyInterface(ABCInterface, Interface):
        def bar(self):
            pass

The ``dir()`` function will include all interface attributes so that ``mock.Mock(spec=IAnimal)`` will work as expected::

    >>> dir(IAnimal)
    ['__abstractmethods__', '__doc__', ..., 'height', 'speak']

The mock_protocol_ package also works well with interfaces.

Sub-Interfaces
--------------

Like ``Protocol``, to specify a sub-interface you must specify the ``Interface`` class again in the base class list.
Only classes that inherit *directly* from ``Interface`` will be considered an interface type.::

    class IWeightyAnimal(IAnimal, Interface):
        weight: float


Concrete Implementations
------------------------

Like ``Protocol``, simply inherit from an interface class in the normal way and write a concrete class.::

    class Animal(IAnimal):
        def __init__(self, height):
            self.height = height

        def speak(self):
            print('hello')

Concrete implementations may implement interface attributes in any way they like: as instance attributes, properties or
custom descriptors, provided that they all exist at the end of ``__init__()``.  Here is another valid implementation::

    class Animal(IAnimal):
        def __init__(self, height):
            self._height = height

        @property
        def height(self):
            return self._height

        def speak(self):
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

    class SilentAnimal(IAnimal):
        def __init__(self, height):
            self.height = height

will issue this warning::

    readme.py:28: UserWarning: Incomplete Implementation: SilentAnimal does not implement speak
    class SilentAnimal(IAnimal):

Trying to create a ``SilentAnimal`` will fail in the standard abc way::

    SilentAnimal()
    InterfaceError: Can't instantiate abstract class SilentAnimal with abstract methods speak

If you have a mixin class that implements part of an interface you can suppress the warnings by adding an class attribute
called ``pi_partial_implementation``.  The value of the attribute is ignored, and the attribute itself is removed from
the class.  For example::

    class HeightMixin(IAnimal):
        pi_partial_implementation = True

        def __init__(self, height):
            self.height = height

will not issue any warnings.

The warning messages are also stored irrespective of any warning module filters (but only if ``get_is_development() returns True``).
The existence of warnings can be tested with waringing messages can be fetched using ``get_missing_method_warnings`` This provides an alternative to raising warnings as errors.
When all your imports are complete you can check if this list is empty.::

    if warnings := pure_iterface.get_missing_method_warnings():
        for warning in warnings:
            print(warning)
        exit(1)

Note that missing properties are NOT checked for as they may be provided by instance attributes.

Interface Subsets
-----------------
Sometimes your code only uses a small part of a large interface.  It can be useful (eg. for test mocking) to specify
the sub part of the interface that your code requires.  This can be done with the ``sub_interface_of`` decorator.::

    @sub_interface_of(IAnimal)
    class IHeight(Interface):
        height: float

    def my_code(h: IHeight):
        return "That's tall" if h.height > 100 else "Not so tall"

The ``sub_interface_of`` decorator checks that the attributes and methods of the smaller interface match the larger interface.
If the larger interface is changed and no longer matches the smaller interface then ``InterfaceError`` is raised during import.
Function signatures must match exactly (not just be compatible).  The decorator will also register the larger interface as
a sub-type of the smaller interface (using ``abc.register``) so that
``isinstance(Animal(), IHeight)`` returns ``True``.

Adaption
========

Registering Adapters
--------------------

Adapters for an interface are registered with the ``adapts`` decorator or with
the ``register_adapter`` function. Take for example an interface ``ISpeaker`` and a
class ``Talker`` and an adapter class ``TalkerToSpeaker``::

    class ISpeaker(Interface):
        def speak(self):
            pass

    class Talker(object):
        def talk(self):
            return 'talk'

    @adapts(Talker)
    class TalkerToSpeaker(ISpeaker):
        def __init__(self, talker):
            self._talker = talker

        def speak(self):
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

      def speak(self):
          return 'lets talk about {}'.format(self.topic)

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

    class IB(IA, Interface):
        bar = None

    @adapts(int):
    class IntToB(IB):
        def __init__(self, x):
            self.foo = self.bar = x

Then  ``IA.adapt(4)`` will use the ``IntToB`` adapter to adapt ``4`` to ``IA`` (unless there is already an adapter
from ``int`` to ``IA``)

Further, if an interface is decorated with ``sub_interface_of``, adapters for the larger interface will be used if
a direct adapter is not found.


Structural Type Checking
========================

Structural_ type checking checks if an object has the attributes and methods defined by the interface.

As interfaces are inherited, you can usually use ``isinstance(obj, MyInterface)`` to check if an interface is provided.
An alternative to ``isinstance()`` is the ``Interface.provided_by(obj)`` classmethod which will fall back to structural type
checking if the instance is not an actual subclass. The structural type-checking does not check function signatures.
Pure interface is stricter than a ``runtime_checkable`` decorated ``Protocol`` in that it differentiates between attributes and methods.::

    class Parrot(object):
        def __init__(self):
            self._height = 43

        @property
        def height(self):
            return self._height

        def speak(self):
            print('hello')

    p = Parrot()
    isinstance(p, IAnimal) --> False
    IAnimal.provided_by(p) --> True

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

When using ``adapt()`` with ``allow_implicit=True``, a warning may be issued informing you that
the structurally typed object should inherit the interface.  The warning is only issued if the interface is implemented by the
class (and not by instance attributes as in the DTO case above) and the warning is only issued once for each
class, interface pair.  For example::

    s = ISpeaker.adapt(Parrot(), allow_implicit=True)
    UserWarning: Class Parrot implements ISpeaker.
    Consider inheriting ISpeaker or using ISpeaker.register(Parrot)

This warning is issued because ``provided_by`` first does an isinstance check and will be faster in this situation.

Dataclass Support
=================
``Interfaces`` can be decorated with the standard library ``dataclasses.dataclass`` decorator.
This will create a dataclass that implements an interface.  For example::

    class IAnimal2(Interface):
        height: float
        species: str

        def speak(self):
            pass

    @dataclasses.dataclass
    class Animal2(IAnimal2):
        def speak(self):
            print('Hello, I am a {} metre tall {}', self.height, self.species)

    a = Animal2(height=4.5, species='Giraffe')

This is done by populating the ``__annotations__`` attribute of all interfaces and all direct interface sub-classes
with the interface attribute names of the class.  Annotation entries are not created for attributes that already exist
on the class.  For example::

    @dataclasses.dataclass
    class FixedHeightAnimal(IAnimal2):
        @property
        def height(self):
            return 12.3

        def speak(self):
            print('Hello, I am a 12.3 metre tall {}', self.height, self.species)

    a = FixedHeightAnimal(species='Dinosaur')

Because ``height`` exists in the class definition, the ``height`` attribute is not added to the ``__annotations__``
attribute of ``FixedHeightAnimal`` and it is ignored by the dataclass decorator.

Interface Type Information
==========================
The ``pure_interface`` module provides these functions for returning information about interface types.

type_is_interface(cls)
    Return ``True`` if ``cls`` is a pure interface, ``False`` otherwise or if ``cls`` is not a class.

get_type_interfaces(cls)
    Returns all interfaces in the ``cls`` mro including ``cls`` itself if it is an interface

get_interface_names(cls)
    Returns a ``frozenset`` of names (methods and attributes) defined by the interface.
    If ``interface`` is not a ``Interface`` subtype then an empty set is returned.

get_interface_method_names(interface)
    Returns a ``frozenset`` of names of methods defined by the interface.
    If ``interface`` is not a ``Interface`` subtype then an empty set is returned

get_interface_attribute_names(interface)
    Returns a ``frozenset`` of names of attributes defined by the interface.
    If ``interface`` is not a ``Interface`` subtype then an empty set is returned


Automatic Adaption
==================
The function decorator ``adapt_args`` adapts arguments to a decorated function to the types given.
For example::

    @adapt_args(foo=IFoo, bar=IBar)
    def my_func(foo, bar=None):
        pass

The types can also be taken from the argument annotations.::

    @adapt_args
    def my_func(foo: IFoo, bar: IBar | None = None):
        pass

This would adapt the ``foo`` parameter to ``IFoo`` (with ``IFoo.optional_adapt(foo))`` and ``bar`` to ``IBar
(using ``IBar.optional_adapt(bar)``)
before passing them to my_func.  ``None`` values are never adapted, so ``my_func(foo, None)`` will work, otherwise
``AdaptionError`` is raised if the parameter is not adaptable.
All arguments to ``adapt_args`` must be specified as keyword arguments::

    @adapt_args(IFoo, IBar)   # NOT ALLOWED
    def other_func(foo, bar):
        pass

Delegation and Composition
==========================

Sometimes when adapting objects to an interface the adapter has to route attributes and methods to another object.
the ``Delegate`` class assists with this task reducing boiler plate code such as::

    def method(self):
        return self.impl.method()

The ``Delegate`` class provides 3 special attributes to route attributes to a child object.  Only attributes and mothods
not defined on the class (or super-classes) are routed.  (Attributes and methods defined on an interface sub-class are not
considered part of the implementation and these attributes are routed.)
Any one or combination of attributes is allowed.

pi_attr_delegates
-----------------

``pi_attr_delegates`` is a dictionary mapping the attribute name of the delegate to either an interface or a list
of attribute names to delegate.
If an interface is given then the list returned by ``get_interface_names()`` is used for the attribute names to route to the delegate object.
For example suppose we want to extend an Animal with a new method ``price``::

    class ExtendedAnimal(Delegate, IAnimal):
        pi_attr_delegates = {'a': IAnimal}

        def __init__(self, a):
            self.a

        def price(self):
            return 'lots'

    a = Animal(5)
    ea = ExtendedAnimal(a)

    ea.height -> 5  # height is in IAnimal and routed to 'ea.a.height'
    ea.speak() -> 'hello'  # speak is in IAnimal and routed to 'ea.a.speak()'
    ea.price() -> 'lots'

The following code is equivalent but won't update with changes to IAnimal::

    class ExtendedAnimal(Delegate):
        pi_attr_delegates = {'a': ['height', 'speak']}

        def __init__(self, a):
            self.a
        ...

pi_attr_mapping
---------------
The above works when the attribute names match. When they don't, you can use the ``pi_attr_mapping`` special attribute.
``pi_attr_mapping`` takes the reverse approach, the key is the attribute and the value is a dotted name of how to route
the lookup.  This provides a lot of flexibility as any number of dots are permitted.
This example is again equivalent to the first Delegate::

    class ExtendedAnimal(Delegate):
        pi_attr_mapping = {'height': 'a.height',
                           'talk': 'a.talk'}

        def __init__(self, a):
            self.a

        def price(self):
            return 'lots'

pi_attr_fallback
----------------
``pi_attr_fallback``, if not ``None``, is treated a delegate for all attributes defined by base interfaces of the class
if there is no delegate, mapping or implementation for that attribute. Again, this is equivalent to the first Delegate.::

    class ExtendedAnimal(Delegate, IAnimal):
        pi_attr_fallback = 'a'

        def __init__(self, a):
            self.a

        def price(self):
            return 'lots'

Note that method and attribute names for all interface classes in ``ExtendAnimal.mro()`` are routed to ``a``.
Methods and properties defined on the delegating class itself take precedence (as one would expect)::

    class MyDelegate(Delegate, IAnimal):
        pi_attr_delegates = {'impl': IAnimal}

        def __init__(self, impl):
            self.impl = impl

        @property
        def height(self):
            return 10

        def speak(self):
            return 'I speak on behalf of the animal'

    d = MyDelegate(a)
    d.height -> 10  # height defined on MyDelegate
    d.speak() -> 'I speak on behalf of the animal'  # speak is defined on MyDelegate

However, attempting to set an instance attribute as an override will just set the attribute on the underlying delegate
instead.  If you want to override an interface attribute using an instance attribute, first define it as a class attribute::

    class MyDelegate(Delegate, IAnimal):
        pi_attr_delegates = {'impl': IAnimal}
        height = None  # prevents delegation of height to `impl`

        def __init__(self, impl):
            self.impl = impl
            self.height = 10

If you supply more than one delegation rule (e.g. both ``pi_attr_mapping`` and ``pi_attr_fallack``) then
 ``pi_attr_delegates`` delegation rules have priority over ``pi_attr_mapping`` delegation rules which have priority over ``pi_attr_fallback``.

Type Composition
----------------
A special case where all delegated attributes are defined in an ``Interface`` is handled by the ``composed_type`` factory function.
``composed_type`` takes 2 or more interfaces and returns a new type that inherits from all the interfaces with a
constructor that takes instances that implement those interfaces (in the same order).  For exmaple::

    AT = composed_type(IAnimal, ITalker)

    a = Animal(5)
    t = Talker()
    a_t = AT(a, t)

    a_t.height
    a_t.talk

    # AT(t, a) -> ValueError - arguments in wrong order.

If the same arguments are passed to ``composed_type`` again the same type is returned. For example::

    AT = composed_type(IAnimal, ITalker)
    AT2 = composed_type(IAnimal, ITalker)

    AT is AT2 -> True

If the interfaces share method or attribute names, then the attribute is routed to the first encountered interface.
For example::

    class Speaker(ISpeaker):
        def speak(self):
            return 'speaker speak'

    SA = composed_type(ISpeaker, IAnimal)
    s = Speaker()
    a = Animal(5)

    sa = SA(s, a)
    sa.speak(3) -> 'speaker speak'  # from s.speak


Types created with ``composed_type`` are ``Delegate`` subclasses with a ``provided_by`` method which returns ``True`` if the
argument provides all the interfaces in the type (even if the argument is not a ``Delegate`` subclasses).::

    AT = composed_type(IAnimal, ITalker)
    TA = composed_type(ITalker, IAnimal)

    a_t = AT(Animal(5), Talker())

    isinstance(a_t, AT) -> True
    isinstance(a_t, TA) -> False
    AT.provided_by(a_t) -> True
    TA.provided_by(a_t) -> True

    class X(IAnimal, ITalker):
        ...

    AT.provided_by(X()) -> True
    TA.provided_by(X()) -> True

MyPy
----

``pure_interface`` does some things that mypy does not understand.  For example mypy does not understand that
all methods in an interface are abstract and will complain about incorrect return types.
For this reason ``pure_interface`` has a mypy plugin.  Unfortunately this plugin does not completely cover all
the capabilities of ``pure_interface`` and some `# type: ignore` comments will be required to get a clean mypy run.

To use the ``pure_interface`` plugin add the following to your `mypy configuration`_ file.::

    [mypy]
    plugins = pure_interface.mypy_plugin

Or your pyproject.toml file::

    [tool.mypy]
    plugins = "pure_interface.mypy_plugin"

Development Flag
================

Much of the empty function and other checking is awesome whilst writing your code but
ultimately slows down production code.
For this reason the ``pure_interface`` module has an ``is_development`` switch with accessor functions.::

    get_is_development()
    set_is_development(is_dev)

``is_development`` defaults to ``True`` if running from source and defaults to ``False`` if bundled into an executable by
py2exe_, cx_Freeze_ or similar tools.

If you call ``set_is_development`` to change this flag it must be set before modules using the ``Interface`` type
are imported or else the change will not have any effect.

If ``is_development`` is ``False`` then:

* Signatures of overriding methods are not checked
* No warnings are issued by the adaption functions
* No incomplete implementation warnings are issued
* The default value of ``interface_only`` is set to ``False``, so that interface wrappers are not created.


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

    **_pi**
        This contains information about the class that is used by this meta-class.
        This attribute is reserved for use by ``pure_interface`` and must not be overridden.


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

    **provided_by** *(obj)*
        Returns ``True`` if *obj* provides this interface (either by inheritance or structurally).

**Delegate**
    Helper class for delegating attribute access to one or more objects.  Attribute delegation is defined by
    using one or more special call attributes ``pi_attr_delegates``, ``pi_attr_mapping`` or ``pi_attr_fallback``.

    **pi_attr_delegates**
        A dictionary mapping implementation attribute to either a list of attributes to delegate to that implementation,
        or an ``Interface`` subclass.  If an ``Interface`` subclass is specifed the names returned by
        ``get_interface_names`` are used instead. For example::

            pi_attr_delegates = {'_impl': ['foo', 'bar']}

        creates implmentations of ``obj.foo`` as ``obj._impl.foo`` and ``obj.bar`` as ``obj._impl.bar``.

    **pi_attr_mapping**
        A dictionary mapping attribute name to dotted lookup path.  Use this if the exposed attribute does not match
        the attribute name on the delegatee or if multiple levels of indirection are requried.  For example::

            pi_attr_mapping = {'foo': '_impl.x',
                               'bar': '_impl.z.y'}

        creates implmentations of ``obj.foo`` as ``obj._impl.x`` and ``obj.bar`` as ``obj._impl.z.y``.

    **pi_attr_fallback**
        When a delegate class implements an interface (or interfaces), ``pi_attr_fallback`` may be used to specify the name the
        implementation attribute for all attributes not otherwise defined on the class or by the methods above.  For example::

            class MyDelgate(Delegate, IAnimal):
                pi_attr_fallback = 'impl'

                def __init__(self, animal):
                    self.impl = animal

        If the delegate does not inherit from an interface then ``pi_attr_fallback`` does nothing.

    **provided_by** *(obj)*
        ``Interface.provided_by`` equivalent for delegates created by ``composed_type``.  It returns ``True``
        if obj provides all the interfaces in the composed type and ``False`` otherwise.


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

**dataclass** *(...)*
    This function is a re-implementation of the standard Python ``dataclasses.dataclass`` decorator.
    In addition to the fields on the decorated class, all annotations on interface base classes are added as fields.
    See the Python dataclasses_ documentation for details on the arguments, they are exactly the same.

**get_is_development()**
    Returns the current value of the "is development" flag.

**set_is_devlopment** *(is_dev)*
    Set to ``True`` to enable all checks and warnings.
    If set to ``False`` then:

    * Signatures of overriding methods are not checked
    * No warnings are issued by the adaption functions
    * No incomplete implementation warnings are issued
    * The default value of ``interface_only`` is set to ``False``, so that interface wrappers are not created.


**get_missing_method_warnings** *()*
    The list of warning messages for concrete classes with missing interface (abstract) method overrides.
    Note that missing properties are NOT checked for as they may be provided by instance attributes.

**composed_type** *(*interface_types)*
    Type factory function that creates a ``Delegate`` subclass that implements all the interfaces via delegates.


Exceptions
----------
**PureInterfaceError**
    Base exception class for all exceptions raised by ``pure_interface``.

**InterfaceError**
    Exception raised for problems with interfaces

**AdaptionError**
    Exception raised for problems with adapters or adapting.


-----------

.. _typing: https://pypi.python.org/pypi/typing
.. _PEP-544: https://www.python.org/dev/peps/pep-0544/
.. _GitHub: https://github.com/seequent/pure_interface
.. _mypy: http://mypy-lang.org/
.. _py2exe: https://pypi.python.org/pypi/py2exe
.. _cx_Freeze: https://pypi.python.org/pypi/cx_Freeze
.. _dataclasses: https://docs.python.org/3/library/dataclasses.html
.. _mock_protocol: https://pypi.org/project/mock-protocol/
.. _Structural: https://en.wikipedia.org/wiki/Structural_type_system
.. _mypy configuration: https://mypy.readthedocs.io/en/stable/config_file.html#config-file

.. [*] We don't talk about the methods on the base ``Interface`` class.  In earlier versions they
   were all on the meta class but then practicality (mainly type-hinting) got in the way.
