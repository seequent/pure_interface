# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import pure_interface


class IAnimal(pure_interface.PureInterface):
    def speak(self, volume):
        pass

    @pure_interface.abstractproperty
    def height(self):
        return None
