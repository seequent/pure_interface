# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import warnings

import pure_interface
from pure_interface import InterfaceError, Concrete  # alias for convenience
import six

try:
    import contracts  # https://pypi.python.org/pypi/PyContracts

    class PureContractType(pure_interface.PureInterfaceType, contracts.ContractsMeta):
        # we need to unwrap the decorators because otherwise we fail the empty function body test
        # inspecting the wrapper.
        _pi_unwrap_decorators = True
        pass

except ImportError:
    warnings.warn('PyContracts not found')

    class PureContractType(pure_interface.PureInterfaceType):
        _pi_unwrap_decorators = True
        pass


@six.add_metaclass(PureContractType)
class ContractInterface(pure_interface.PureInterface):
    pass
