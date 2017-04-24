==============
pure_interface
==============

A Python interface library that disallows function body content on interfaces and supports adaption.

Features:
    * Prevents implementation code in an interface class
    * Works just like a python abc abstract classes (to get IDE support)
    * Allows concrete implementations flexibility to implement abstract properties as attributes.
    * Treats abc interfaces that do not include any implementation as a pure interface type.
      This means that ``class C(PureInterface, ABCInterface)`` will be a pure interface if the abc interface meets the
      no function body content criteria.
    * Fallback to duck-type checking for ``isinstance(a, Interface)``
    * Fallback to duck-type checking for ``issubclass(C, Interface)``
    * Ensure that method overrides have a the same signature (optional)
    * Option to warn if ``isinstance`` or ``issubclass`` did a duck-type check when inheritance or registering would wok.
    * Option to turn off method signature checking.
    * Support interface adapters.
    * Support python 2.7 and 3.5+

A note on the name
------------------
The phrase *pure interface* applies only to the first design goal - a class that defines only an interface with no
implementation is a pure interface.  In every other respect the zen of 'practicality beats purity' applies, particularly
with respect to retrofitting interfaces to existing code.

Installation
------------
You can install released versions of pure_interface using pip::

    pip install pure_interface

or you can grab the source code from GitHub_.

.. _GitHub: https://github.com/tim-mitchell/pure_interface

Defining a Pure Interface
-------------------------
For simplicity in these examples we assume that the entire pure_interface namespace has been imported ::

    from pure_interface import *

To define an interface, simply inherit from the class ``PureInterface`` and leave all method bodies empty::

    class MyInterface(PureInterface):
        def method_one(self):
            pass

        @abstractmethod
        def method_two(self):
            pass

        @property
        def property_one(self):
            pass

        @abstractproperty
        def property_two(self):
            pass

As ``PureInterface`` is a subtype of ``abc.ABC`` the ``abstractmethod`` and ``abstractproperty`` decorators work as expected.
For convenience the ``abc`` module abstract decorators are included in the ``pure_interface`` namespace, and on Python 2.7
``abstractclassmethod`` and ``abstractstaticmethod`` are also available.

However these decorators are optional as **ALL** methods and properties on a pure interface are abstract ::

    >>> MyInterface()
    TypeError: Can't instantiate abstract class MyInterface with abstract methods method_one, method_two, property_one, property_two

Including abstract decorators in your code can be useful for reminding yourself (and telling your IDE) that you need
to override those methods.  Another common way of informing an IDE that a method needs to be overridden is for
the method to raise ``NotImplementedError``.  For this reason methods that just raise ``NotImplementedError`` are also
considered empty.

Including code in a method will result in an ``InterfaceError`` being raised when the module is imported. For example::

    >>> class BadInterface(PureInterface):
    >>>     def method_one(self):
    >>>         print('hello')

    InterfaceError: Function "method_one" is not empty

Instance Checking
-----------------
pure_interface types will fall back to duck-type checking if the instance is not an actual (or registered) subclass.::

    class IAnimal(PureInterface):
        @abstractproperty
        def height(self):

        def speak(self, volume):
            pass

    class Animal2(object):
        def __init__(self):
            self.height = 43

        def speak(self, volume):
            print('hello')

    a = Animal2()
    isinstance(a, IAnimal) --> True

PureInterface supports the abc ``register`` method to register classes as subtypes of an interface.::

    IAnimal.register(Animal2)

Registering a class in this way will make ``isinstance`` calls faster.

The duck-type checking makes working with data transfer objects (DTO's) much easier.::

    class IMyDataType(PureInterface):
        @property
        def thing(self):
            pass

    class DTO(object):
        pass

    d = DTO()
    d.thing = 'hello'
    isinstance(d, IMyDataType) --> True
    e = DTO()
    e.something_else = True
    isinstance(e, IMyDataType) --> False

For ``PureInterface`` types, ``isinstance(d, IMyDataType)`` means ``d`` provides the interface,
it does not imply that ``issubclass(type(d), IMyDataType)`` is ``True``.  However this is the case
with ``ABC`` interfaces already.

Concrete Implementations
------------------------
Simply inheriting from a pure interface and writing a concrete class will result in an ``InterfaceError`` exception as
``pure_interface`` will assume you are creating a sub-interface. To tell ``pure_interface`` that a type should be concrete
simply inherit from object as well (or anything else that isn't a ``PureInterface``).  For example::

    class MyImplementation(object, MyInterface):
        def method_one(self):
            print('hello')

**Exception:** Mixing a PureInterface class with an abc.ABC interface class that only defines abstract methods and properties
that satisfy the empty method criteria can will result in a type that is considered a pure interface.::

    class ABCInterface(abc.ABC):
        @abstractmethod
        def method_one(self):
            pass

    class MyPureInterface(ABCInterface):
        def method_two(self):
            pass

Concrete implementations may implement interface properties as normal attributes,
provided that they are all set in the constructor::

  class MyInterface(PureInterface)
      @property
      def thing(self):
         pass

  class MyImplementation(MyInterface):
      def __init__(self, thing):
          self.thing = thing

This can simplify implementations greatly when there are lots of properties on an interface.

Adaption
--------
Adapters for an interface are registered with the
``adapts`` decorator or with the ``register_adapter`` function. Take for example an interface ``ISpeaker`` and a class
``Talker`` and an adapter class ``TalkerToSpeaker``::

    class ISpeaker(PureInterface):
        def speak(self, volume):
            pass

    class Talker(object):
        def talk(self):
            return 'talk'

    @adapts(Talker, ISpeaker)
    class TalkerToSpeaker(object, ISpeaker):
        def __init__(self, talker):
            self._talker = talker

        def speak(self, volume):
            return self._talker.talk()

The ``adapts`` decorator call above is equivalent to::

    register_adapter(TalkerToSpeaker, Talker, ISpeaker)

Adapter factory functions can be decorated too::

    @adapts(Talker, ISpeaker)
    def talker_to_speaker(talker):
        return TalkerToSpeaker(talker)

The ``adapt_to_interface`` function will adapt an object to the given interface if possible
and raise ``ValueError`` if not.::

    speaker = adapt_to_interface(talker, ISpeaker)

Alternatively, you can use the ``adapt`` method on the interface class::

    speaker = ISpeaker.adapt(talker)

If you want to get ``None`` rather than an exception then use::

    speaker = adapt_to_interface_or_none(talker, ISpeaker)

or::

    speaker = ISpeaker.adapt_or_none(talker)

You can filter a list of objects, returning a generator of those that implement an interface using
``filter_adapt(objects, interface)``::

   list(filter_adapt([None, Talker(), a_speaker, 'text'], ISpeaker) -> [<TalkerToSpeaker>, a_speaker]

Options
-------
The ``pure_interface`` module has 4 boolean flags which control optional functionality.
Note that most of these flags must be set before modules using the ``PureInterface`` type
are imported or else the changes will not have any effect

ADAPT_TO_INTERFACE_ONLY
    If ``True`` then ``adapt_to_interface`` will return an object which provides ONLY
    the functions and properties specified by the interface.  For example given the
    following implementation of the ``ISpeaker`` interface above::

      class TopicSpeaker(ISpeaker):
          def __init__(self, topic):
              self.topic = topic

          def speak(self, volume):
              return 'lets talk about {} very {}'.format(self.topic, volume)

    Then::

      topic_speaker = TopicSpeaker('python')
      speaker = adapt_to_interface(ts, ISpeaker)
      speaker is topic_speaker  --> False
      speaker.topic --> AttributeError("ISpeaker interface has no attribute topic")

    If ``False`` then the object itself, or a registered adapter class is returned::

      topic_speaker = TopicSpeaker('python')
      speaker = adapt_to_interface(ts, ISpeaker)
      speaker is topic_speaker  --> True
      speaker.topic --> 'Python'

    Accessing the ``topic`` attribute on an ``ISpeaker`` may work for all current implementations
    of ISpeaker, but this code will likely break at some inconvenient time in the future.

    **Default:** ``not hasattr(sys, 'frozen')`` (``True`` if running from source, ``False`` if bundled into an executable)

ONLY_FUNCTIONS_AND_PROPERTIES
    If ``True`` this ensures that interface types only contain
    functions (methods) and properties and no other class attributes.  For example::

      class MyInterface(PureInterface):
          disallowed = True

    would not be permitted.

    **Default:** ``False``

CHECK_METHOD_SIGNATURES
    If ``True`` method overrides are checked for compatibility with the interface.
    This means that argument names must match exactly and that no new non-optional
    arguments are present in the override.  This enforces that calling the method
    with interface parameters will aways work.
    For example, given the method::

      def speak(self, volume):

    Then these overrides will all fail the checks::

       def speak(self):  # too few parameters
       def speak(self, loudness):  # name does not match
       def speak(self, volume, language):  # extra required argument

    However new optional parameters are permitted::

      def speak(self, volume, language='doggy speak')

    **Default:** ``not hasattr(sys, 'frozen')`` (``True`` if running from source, ``False`` if bundled into an executable)

WARN_ABOUT_UNNCESSARY_DUCK_TYPING
    If ``True`` then when doing ``isinstance(a, Interface)`` or ``issubclass(A, Interface)``,
    a warning message is emitted if an unnecessary duck-type check is done.
    For example::

        class ISpeaker(PureInterface):
            def speak(self, volume):
                pass

        class Speaker(object):
            def speak(self, volume):
                return 'speak'

        s = Speaker()
        isinstance(s, ISpeaker)  --> True
        UserWarning: Class Speaker implements ISpeaker.
        Consider inheriting ISpeaker or using ISpeaker.register(Speaker)

    **Default:** ``not hasattr(sys, 'frozen')`` (``True`` if running from source, ``False`` if bundled into an executable)
