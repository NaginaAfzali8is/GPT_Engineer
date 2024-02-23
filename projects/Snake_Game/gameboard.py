from point import Point
import random

class GameBoard:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def get_center_point(self):
        return Point(self.width // 2, self.height // 2)

    def generate_food_position(self, snake):
        while True:
            position = Point(random.randint(0, self.width - 1), random.randint(0, self.height - 1))
            if position not in snake.body:
                return position

    def is_point_inside(self, point):
        return 0 <= point.x < self.width and 0 <= point.y < self.height

    def render(self, snake, food):
        # This method should be implemented to render the game board
        pass