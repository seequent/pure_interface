# --------------------------------------------------------------------------------------------
#  Copyright (c) Bentley Systems, Incorporated. All rights reserved.
#  See COPYRIGHT.md in the repository root for full copyright notice.
# --------------------------------------------------------------------------------------------

import pure_interface


class IAnimal(pure_interface.Interface):
    def speak(self, volume) -> str:
        pass

    @property
    def height(self):
        return None
