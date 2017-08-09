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
    * Fallback to duck-type checking for ``Interface.provided_by(a)``
    * Ensure that method overrides have a the same signature
    * Warns if ``provided_by`` did a duck-type check when inheritance or registering would work.
    * Support interface adaption.
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

.. _GitHub: https://github.com/aranzgeo/pure_interface

Defining a Pure Interface
=========================

For simplicity in these examples we assume that the entire pure_interface namespace has been imported ::

    from pure_interface import *

To define an interface, simply inherit from the class ``PureInterface`` and leave all method bodies empty::

    class IAnimal(PureInterface):
        @property
        def height(self):
            pass

        def speak(self, volume):
            pass


As ``PureInterface`` is a subtype of ``abc.ABC`` the ``abstractmethod`` and ``abstractproperty`` decorators work as expected.
For convenience the ``abc`` module abstract decorators are included in the ``pure_interface`` namespace, and
on Python 2.7 ``abstractclassmethod`` and ``abstractstaticmethod`` are also available.

However these decorators are optional as **ALL** methods and properties on a pure interface are abstract ::

    IAnimal()
    TypeError: Can't instantiate abstract class IAnimal with abstract methods height, speak

Including abstract decorators in your code can be useful for reminding yourself (and telling your IDE) that you need
to override those methods.  Another common way of informing an IDE that a method needs to be overridden is for
the method to raise ``NotImplementedError``.  For this reason methods that just raise ``NotImplementedError`` are also
considered empty.

Including code in a method will result in an ``InterfaceError`` being raised when the module is imported. For example::

    class BadInterface(PureInterface):
        def method(self):
            print('hello')

    InterfaceError: Function "method" is not empty

Concrete Implementations
========================

Simply inheriting from a pure interface and writing a concrete class will result in an ``InterfaceError`` exception
as ``pure_interface`` will assume you are creating a sub-interface. To tell ``pure_interface`` that a type should be
concrete simply inherit from ``object`` as well (or anything else that isn't a ``PureInterface``).  For example::

    class Animal(object, IAnimal):
        def __init__(self, height):
            self._height = height

        @property
        def height(self):
            return self._height

        def speak(self, volume):
            print('hello')

**Exception:** Mixing a ``PureInterface`` class with an ``abc.ABC`` interface class that only defines abstract methods
and properties that satisfy the empty method criteria will result in a type that is considered a pure interface.::

    class ABCInterface(abc.ABC):
        @abstractmethod
        def foo(self):
            pass

    class MyPureInterface(ABCInterface):
        def bar(self):
            pass

Concrete implementations may implement interface properties as normal attributes,
provided that they are all set in the constructor::

    class Animal2(object, IAnimal):
        def __init__(self, height):
            self.height = height

        def speak(self, volume):
            print('hello')

This can simplify implementations greatly when there are lots of properties on an interface.

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

However new optional parameters are permitted::

  def speak(self, volume, language='doggy speak')

Interface Checking
==================

As interfaces are inherited, you can usually use ``isinstance(obj, MyInterface)`` to check if an interface is provided.
An alternative to ``isinstance()`` is the ``PureInterface.provided_by(obj)`` classmethod which will fall back to duck-type
checking if the instance is not an actual subclass. The duck-type checking does not check function signatures.::

    class Parrot(object):
        def __init__(self):
            self.height = 43

        def speak(self, volume):
            print('hello')

    p = Parrot()
    isinstance(p, IAnimal) --> False
    IAnimal.provided_by(p) --> True

The duck-type checking makes working with data transfer objects (DTO's) much easier.::

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

The decorated adapter (whether class for function) must be callable with a single parameter - the object to adapt.

Adapting Objects
----------------

The ``PureInterface.adapt`` method will adapt an object to the given interface
such that ``Interface.provided_by(obj)`` is ``True`` or raise ``ValueError`` if no adapter could be found.  For example::

    speaker = ISpeaker.adapt(talker)
    ISpeaker.provided_by(speaker)  --> True

If you want to get ``None`` rather than an exception then use::

    speaker = ISpeaker.adapt_or_none(talker)

You can filter a list of objects, returning a generator of those that provide an interface
using ``filter_adapt(objects)``::

   list(ISpeaker.filter_adapt([None, Talker(), a_speaker, 'text']) --> [TalkerToSpeaker, a_speaker]

By default the adaption functions will return an object which provides ONLY
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

This is controlled by the optional ``interface_only`` parameter which defaults to ``True``.
Pass ``interface_only=False`` if you want the actual adapted object rather than a wrapper::

  speaker = ISpeaker.adapt(topic_speaker, interface_only=False)
  speaker is topic_speaker  --> True
  speaker.topic --> 'Python'

Accessing the ``topic`` attribute on an ``ISpeaker`` may work for all current implementations
of ISpeaker, but this code will likely break at some inconvenient time in the future.

Note that objects that implicitly provide an interface by duck-typing may be returned by the adaption functions.
When this happens a warning is issued informing that the duck-typed object should inherit the interface.
The warning is only issued once for each class, interface pair.  For example::

    a = Animal()
    s = ISpeaker.adapt(a)
    UserWarning: Class Animal implements ISpeaker.
    Consider inheriting ISpeaker or using ISpeaker.register(Animal)

Development Flag
================

Much of the empty function and other checking is awesome whilst writing your code but
ultimately slows down production code.
For this reason the ``pure_interface`` module has an IS_DEVELOPMENT switch.::

    IS_DEVELOPMENT = not hasattr(sys, 'frozen')

IS_DEVELOPMENT defaults to ``True`` if running from source and default to ``False`` if bundled into an executable by
py2exe_, cx_Freeze_ or similar tools.

.. _py2exe: https://pypi.python.org/pypi/py2exe

.. _cx_Freeze: https://pypi.python.org/pypi/cx_Freeze


If you manually change this flag it must be set before modules using the ``PureInterface`` type
are imported or else the change will not have any effect.

If ``IS_DEVELOPMENT`` if ``False`` then:

    * Signatures of overriding methods are not checked
    * No warnings are issued by the adaption functions
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

