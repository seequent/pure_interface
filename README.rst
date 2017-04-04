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
The ``abc`` module abstract decorators are included in the ``pure_interface`` namespace, and on Python 2.7 
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


Concrete Implementations
------------------------
Simply inheriting from a pure interface and writing a concrete class will result in an ``InterfaceError`` exception as
``pure_interface`` will assume you are creating a sub-interface. To tell ``pure_interface`` that a type should be concrete
simply inherit from object as well (or anything else that isn't a ``PureInterface``).  For example::

    class MyImplementation(object, MyInterface):
        def method_one(self):
            print('hello')
        ...

**Exception:** Mixing a PureInterface class with an abc.ABC interface class that only defines abstract methods and properties 
that satisfy the empty method criteria can will result in a type that is considered a pure interface.::

    class ABCInterface(abc.ABC):
        @abstractmethod
        def method_one(self):
            pass
            
        def method_two(self):
            pass
         

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

    speaker = adapter_to_interface(Talker(), ISpeaker)
    
If you want to get ``None`` rather than an exception use ``adapt_to_interface_or_none`` instead.

You can filter a list of objects, returning a generator of those that implement an interface using
``filter_adapt(objects, interface)``::

   list(filter_adapt([None, Talker(), a_speaker, 'text'], ISpeaker) -> [<TalkerToSpeaker>, a_speaker]

