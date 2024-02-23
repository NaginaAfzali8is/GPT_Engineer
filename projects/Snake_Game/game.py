from snake import Snake
from food import Food
from gameboard import GameBoard
from direction import Direction
import random
import time

class Game:
    def __init__(self):
        self.board = GameBoard(20, 20)  # Assuming a 20x20 board
        self.snake = Snake(self.board.get_center_point())
        self.food = Food(self.board.generate_food_position(self.snake))
        self.score = 0
        self.is_game_over = False

    def start(self):
        while not self.is_game_over:
            self.board.render(self.snake, self.food)
            self.process_input()
            self.update()
            time.sleep(0.1)  # Game tick rate

    def process_input(self):
        # This method should be implemented to handle user input
        pass

    def update(self):
        self.snake.move()
        if self.snake.head == self.food.position:
            self.snake.grow()
            self.food.reposition(self.board.generate_food_position(self.snake))
            self.score += 1
        elif not self.board.is_point_inside(self.snake.head) or self.snake.has_collided_with_self():
            self.is_game_over = True

    def end_game(self):
        print(f"Game Over! Your score: {self.score}")