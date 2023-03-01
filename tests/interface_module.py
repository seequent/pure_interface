import pure_interface


class IAnimal(pure_interface.Interface):
    def speak(self, volume):
        pass

    @property
    def height(self):
        return None
