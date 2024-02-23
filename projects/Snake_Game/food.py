from point import Point

class Food:
    def __init__(self, position):
        self.position = position

    def reposition(self, new_position):
        self.position = new_position