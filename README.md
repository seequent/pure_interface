# pure_interface
A Python abc (abstract base class) implementation that disallows function body content on interfaces.

The goals of this package are:
* to prevent implementation code in an interface class
* work just like a python abc interface (to get IDE support)
* allow concrete implementations to use attributes instead of properties (to make retrofitting of interfaces easier)
* work nicely with abc interfaces that do not include any implementation.
  This means that `class C(PureInterface, ABCInterface)` will be a pure interface if the abc interface meets the 
  no function body content criteria.
* fallback to duck-type checking for `isinstance(a, Interface)` (or `issubclass(A, Interface)`) 
(so that duck typing still works.)
* Ensure that method overrides have a the same signature (optional)
* Release mode and warning switches. E.g. warn if using ducktype isinstance.  Turn off method signature checking when frozen.
* Support interface adapters/mappers
* support python 2.7 and 3.2+

## A note on the name

The phrase _pure interface_ applies only to the first design goal - a class that defines only an interface with no 
implementation is a pure interface.  In every other respect the zen of 'practicality beats purity' applies, particularly
with respect to retrofitting interfaces to existing code.

## Installation
TODO: Make this true  
You can install released versions of pure_interface using pip:

    pip install pure_interface
    
or you can grab the source code from [GitHub](https://github.com/tim-mitchell/pure_interface).
 
# Defining a Pure Interface
For simplicity in these examples we assume that the entire pure_interface namespace has been imported :

    from pure_interface import *

To define an interface, simply inherit from the class `PureInterface` and leave all method bodies empty:
    
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
            
As `PureInterface` is a subtype of `abc.ABC` the `abstractmethod` and `abstractproperty` decorators work as expected.
The `abc` module abstract decorators are included in the `pure_interface` namespace, and on Python 2.7 
`abstractclassmethod` and `abstractstaticmethod` are also available.
However these decorators are optional as **ALL** methods and properties on a pure interface are abstract :

    >>> MyInterface()
    TypeError: Can't instantiate abstract class MyInterface with abstract methods method_one, method_two, property_one, property_two

Including abstract decorators in your code can be useful for reminding yourself (and telling your IDE) that you need
to override those methods.  Another common way of informing an IDE that a method needs to be overridden is for
the method to raise `NotImplementedError`.  For this reason methods that just raise `NotImplementedError` are also
considered empty.

Including code in a method will result in an `InterfaceError` being raised when the module is imported. For example:

    >>> class BadInterface(PureInterface):
    >>>     def method_one(self):
    >>>         print('hello')
                
    pure_interface.InterfaceError: Function "method_one" is not empty

# Concrete Implementations

Simply inheriting from a pure interface and writing a concrete class will result in an `InterfaceError` exception as
`pure_interface` will assume you are creating a sub-interface. To tell `pure_interface` that a type should be concrete
simply inherit from object as well (or anything else that isn't a `PureInterface`).  For example:

    class MyImplementation(object, MyInterface):
        def method_one(self):
            print('hello')
        ...

**Exception:** Mixing a PureInterface class with an abc.ABC interface class that only defines abstract methods and properties 
that satisfy the empty method criteria can will result in a type that is considered a pure interface. 

    class ABCInterface(abc.ABC):
        @abstractmethod
        def method_one(self):
            pass
            
    class MyPureInterface(PureInterface, ABCInterface):
        def method_two(self):
            pass
         
# Adaption

This topic comming in a commit near you.