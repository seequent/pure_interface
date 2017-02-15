# pure_interface
Python abc (abstract base class) implementation that disallows function body content on interfaces.

The goals of this package are:
* to prevent implementation code in an interface class
* work just like a python abc interface (to get IDE support)
* allow concrete implementations to use attributes instead of properties (to make retrofitting of interfaces easier)
* work nicely with plain abc interfaces that do not include any implementation.
  This means that `class C(PureInterface, ABCInterface)` will be a pure interface if the abc interface meets the 
  no function body content criteria.
* fallback to duck-type checking for `isinstance(a, PureInterface)` (or `PureInterface.provided_by(a)`) 
(for easier duck typing.)
* Ensure that method overrides have a the same signature (optional?)
* Release mode and warning switches. E.g. warn if using ducktype isinstance.  Turn off method signature checking  
* Support interface adapters/mappers
* support python 2.7 and 3.5+

A note on the name
------------------
The phrase _pure interface_ applies only to the first design goal - a class that defines only an interface with no 
implementation is a pure interface.  In every other respect the zen of 'practicality beats purity' applies.


