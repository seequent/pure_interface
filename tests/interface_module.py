import pure_interface


class IAnimal(pure_interface.Interface):
    def speak(self, volume) -> str:
        pass

    @property
    def height(self):
        return None
