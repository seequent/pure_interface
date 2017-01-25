# pure_interface
Python abc (abstract base class) implementation that disallows function body content on interfaces.

The goals of this package are:
* to prevent implementation code to in an interface class
* work just like a python abc interface (to get IDE support)
* allow concrete implementations to use attributes instead of properties (to make retrofitting of interfaces easier)
* work nicely with plain abc interfaces that do not include any implementation
* fallback to duck-type checking for `isinstance(a, PureInterface)` (or `PureInterface.provided_by(a)`) 
(for easier duck typing.)
* Ensure that method overrides have a the same signature (optional?)
* Support interface adapters/mappers
* support python 2.7 and 3.5+
