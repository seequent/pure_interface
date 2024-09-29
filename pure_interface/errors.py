# --------------------------------------------------------------------------------------------
#  Copyright (c) Bentley Systems, Incorporated. All rights reserved.
#  See COPYRIGHT.md in the repository root for full copyright notice.
# --------------------------------------------------------------------------------------------


class PureInterfaceError(Exception):
    """All exceptions raised by this module are subclasses of this exception"""

    pass


class InterfaceError(PureInterfaceError, TypeError):
    """An error with an interface class definition or implementation"""

    pass


class AdaptionError(PureInterfaceError, ValueError):
    """An adaption error"""

    pass
