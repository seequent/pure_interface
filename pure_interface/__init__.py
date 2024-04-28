from .errors import PureInterfaceError, InterfaceError, AdaptionError
from .interface import Interface, InterfaceType
from .interface import type_is_interface, get_type_interfaces
from .interface import get_interface_names, get_interface_method_names, get_interface_attribute_names
from .interface import get_is_development, set_is_development, get_missing_method_warnings
from ._sub_interface import sub_interface_of
from .adaption import adapts, register_adapter, AdapterTracker, adapt_args
from .delegation import Delegate

__version__ = '8.0.2'
