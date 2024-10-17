# --------------------------------------------------------------------------------------------
#  Copyright (c) 2024 Bentley Systems, Incorporated. All rights reserved.
# --------------------------------------------------------------------------------------------

from ._sub_interface import sub_interface_of
from .adaption import AdapterTracker, adapt_args, adapts, register_adapter
from .delegation import Delegate
from .errors import AdaptionError, InterfaceError, PureInterfaceError
from .interface import (
    Interface,
    InterfaceType,
    get_interface_attribute_names,
    get_interface_method_names,
    get_interface_names,
    get_is_development,
    get_missing_method_warnings,
    get_type_interfaces,
    set_is_development,
    type_is_interface,
)

__version__ = "8.0.3"  # Don't change this manually - run `bump-my-version bump [major|minor|patch]` instead
