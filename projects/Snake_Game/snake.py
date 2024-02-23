from point import Point
from direction import Direction

class Snake:
    def __init__(self, initial_position):
        self.body = [initial_position]
        self.direction = Direction.RIGHT

    @property
    def head(self):
        return self.body[0]

    def move(self):
        head_x, head_y = self.head
        if self.direction == Direction.UP:
            head_y -= 1
        elif self.direction == Direction.DOWN:
            head_y += 1
        elif self.direction == Direction.LEFT:
            head_x -= 1
        elif self.direction == Direction.RIGHT:
            head_x += 1
        new_head = Point(head_x, head_y)
        self.body.insert(0, new_head)
        self.body.pop()

    def grow(self):
        self.body.append(self.body[-1])

    def has_collided_with_self(self):
        return len(self.body) != len(set(self.body))

    def change_direction(self, new_direction):
        # Prevent the snake from reversing onto itself
        if new_direction == Direction.UP and self.direction != Direction.DOWN:
            self.direction = new_direction
        elif new_direction == Direction.DOWN and self.direction != Direction.UP:
            self.direction = new_direction
        elif new_direction == Direction.LEFT and self.direction != Direction.RIGHT:
            self.direction = new_direction
        elif new_direction == Direction.RIGHT and self.direction != Direction.LEFT:
            self.direction = new_direction