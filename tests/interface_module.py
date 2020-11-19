# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pure_interface


class IAnimal(pure_interface.Interface):
    def speak(self, volume):
        pass

    @property
    def height(self):
        return None
