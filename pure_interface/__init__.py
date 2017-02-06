
try:
    from abc import abstractmethod, abstractproperty, abstractclassmethod, abstractstaticmethod
except NameError:
    from abc import abstractmethod, abstractproperty


class InterfaceError(Exception):
    pass


class PureInterface(object):
    pass
