# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import warnings

import pure_interface
from pure_interface import InterfaceError  # alias for convenience

try:
    import contracts  # https://pypi.python.org/pypi/PyContracts

    class ContractType(pure_interface.InterfaceType, contracts.ContractsMeta):
        # we need to unwrap the decorators because otherwise we fail the empty function body test
        # inspecting the wrapper.
        _pi_unwrap_decorators = True
        pass

except ImportError:
    warnings.warn('PyContracts not found')

    class ContractType(pure_interface.InterfaceType):
        _pi_unwrap_decorators = True
        pass


class ContractInterface(pure_interface.Interface, metaclass=ContractType):
    pass
