# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import warnings

import pure_interface
from pure_interface import InterfaceError
import six

try:
    import contracts  # https://pypi.python.org/pypi/PyContracts

    class PureContractType(pure_interface.PureInterfaceType, contracts.ContractsMeta):
        _pi_unwrap_decorators = True
        pass

except ImportError:
    warnings.warn('PyContracts not found')

    class PureContractType(pure_interface.PureInterfaceType):
        _pi_unwrap_decorators = True
        pass


@six.add_metaclass(PureContractType)
class ContractInterface(object):
    pass

ContractInterface._pi.type_is_pure_interface = True
