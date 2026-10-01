import contextlib
import io
import os
import random
import runpy
from abc import ABC, abstractmethod
from unittest import mock

import cv2
import numpy as np


class ScrambleScript:
    #runs the image scrambler
    PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),"assignment3imagescramble.py")

    def run(self, image_path, grid):
        output = io.StringIO()
        answers = [str(grid), image_path]  
        try:
            with (contextlib.redirect_stdout(output),
                    mock.patch("builtins.input", side_effect=answers),
                    mock.patch.object(cv2, "imwrite", return_value=True),
                    mock.patch.object(cv2, "imshow"),
                    mock.patch.object(cv2, "waitKey", return_value=0),
                    mock.patch.object(cv2, "destroyAllWindows")):
                
                return runpy.run_path(self.PATH, run_name="scramble_script")
       
        except (SystemExit, Exception) as err:
            if "Could not load" in output.getvalue():
                raise ValueError("The selected file is not a valid image.")
            raise ValueError(f"The image could not be scrambled: {err}")


class Tile:
    #defines original tiles orientation
    def __init__(self, pixels, home_index):
        self._pixels = pixels            
        self._home_index = home_index    
        self._rotation = 0               
        self._flipped = False

    @property
    #reads the original position of the tile so it can be used later
    def home_index(self):
        return self._home_index

   #rotates the tile
    def rotate_cw(self, quarter_turns=1):
        self._rotation = (self._rotation + quarter_turns) % 4

    #appplies the horizontal flips 
    def flip_horizontal(self):
        self._rotation = (-self._rotation) % 4
        self._flipped = not self._flipped

    #applies the vertical flips
    def flip_vertical(self):
        self.flip_horizontal()
        self.rotate_cw(2)

    #puts a tile back to its correct orientation
    def reset_orientation(self):
        self._rotation = 0
        self._flipped = False

    #check if the tile is in its original orentation
    def is_upright(self):
        return self._rotation == 0 and not self._flipped

    #renders the picture so it can be displayed
    def render(self):
        image = self._pixels
        if self._flipped:
            image = cv2.flip(image, 1)
        for _ in range(self._rotation):
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)


        height, width = self._pixels.shape[:2]
        if image.shape[:2] != (height, width):
            image = cv2.resize(image, (width, height))
        return image


class Transformation(ABC):

    @abstractmethod
    def apply(self, slots):
        pass
    @abstractmethod
    def describe(self):
        pass
    # reads the transformations applied 
    @staticmethod
    def from_script(entry):
        kind = entry[0]
        if kind == "swap":
            return SwapTransformation(entry[1], entry[2])
        if kind == "rotate":
            return RotateTransformation(entry[1], entry[2] // 90)
        if kind == "flip":
            return FlipTransformation(entry[1], entry[2] == "horizontal")
        raise ValueError(f"Unknown transformation: {entry}")


class SwapTransformation(Transformation):
    #applies the transformation
    def __init__(self, first, second):
        self._first = first
        self._second = second

    def apply(self, slots):
        a, b = self._first, self._second
        slots[a], slots[b] = slots[b], slots[a]

    def describe(self):
        return f"Swap {self._first} <-> {self._second}"


class RotateTransformation(Transformation):
    #applies the roatitions
    def __init__(self, index, quarter_turns):
        self._index = index
        self._quarter_turns = quarter_turns  # 1, 2 or 3 -> 90, 180, 270

    def apply(self, slots):
        slots[self._index].rotate_cw(self._quarter_turns)

    def describe(self):
        return f"Rotate {self._index} by {self._quarter_turns * 90} deg"


class FlipTransformation(Transformation):
    # applies the flips
    def __init__(self, index, horizontal):
        self._index = index
        self._horizontal = horizontal

    def apply(self, slots):
        if self._horizontal:
            slots[self._index].flip_horizontal()
        else:
            slots[self._index].flip_vertical()

    def describe(self):
        direction = "horizontally" if self._horizontal else "vertically"
        return f"Flip {self._index} {direction}"


class PuzzleBoard:

    MAX_HINTS = 3
    # creates a variables for all the requierd functions the game board needs
    def __init__(self, original_image, grid_size, tile_width, tile_height):
        self._original = original_image
        self._size = grid_size
        self._tile_width = tile_width
        self._tile_height = tile_height
        self._moves = 0
        self._hints_used = 0
        self._hint = None           
        self._slots = [Tile(pixels, index) for index, pixels in enumerate(self._cut_tiles())]

    @classmethod
    # creates a scrambled puzzle board using the script generator
    def from_script(cls, image_path, grid_size, attempts=20):
        script = ScrambleScript()
        board = None
        for _ in range(attempts):
            result = script.run(image_path, grid_size)
            board = cls(result["image"], result["grid"], result["tile_width"], result["tile_height"])
            board.scramble([Transformation.from_script(entry) for entry in result["transformations"]])
            if not board.solved:
                break
        return board

    # cuts the original image into individual tile pixel arrays
    def _cut_tiles(self):
        tiles = []
        for y in range(self._size):
            for x in range(self._size):
                x1 = x * self._tile_width
                y1 = y * self._tile_height
                tiles.append(self._original[y1:y1 + self._tile_height, x1:x1 + self._tile_width].copy())
        return tiles

    @property
    #Gets the original image
    def original_image(self):
        return self._original

    @property
    # gets the grid size dimensions
    def size(self):
        return self._size

    @property
    # gets the width of a single tile in pixels
    def tile_width(self):
        return self._tile_width

    @property
    #gets the hieght of a single tile in pixels
    def tile_height(self):
        return self._tile_height

    @property
    #gets the total number of moves made
    def moves(self):
        return self._moves

    @property
    #calculates the remaining hints left
    def hints_left(self):
        return self.MAX_HINTS - self._hints_used

    @property
    #gets the current active hint
    def hint(self):
        return self._hint

    @property
    #counts how many tiles are in the wrong place or orientation
    def incorrect_count(self):
        return sum(1 for i in range(len(self._slots)) if not self.is_correct(i))

    @property
    #checks if all tiles are correctly placed
    def solved(self):
        return self.incorrect_count == 0

    # checks if a specific slot holds its correct tile in the right orientation
    def is_correct(self, position):
        tile = self._slots[position]
        return tile.home_index == position and tile.is_upright()


    # applies a list of transformation objects to scramble the board
    def scramble(self, transformations):
        for transformation in transformations:
            transformation.apply(self._slots)

    # swaps the positions of two tiles on the board
    def swap(self, first, second):
        if self.solved:
            return
        self._slots[first], self._slots[second] = (self._slots[second], self._slots[first])
        self._finish_move()

    # rotates a tile at a specific position clockwise
    def rotate(self, position):
        if self.solved:
            return
        self._slots[position].rotate_cw(1)
        self._finish_move()

    # flips a tile horizontally at a specific position
    def flip_horizontal(self, position):
        if self.solved:
            return
        self._slots[position].flip_horizontal()
        self._finish_move()

    # increments the move counter and resets the current active hint
    def _finish_move(self):
        self._moves += 1
        self._hint = None 

    # generates a hint for a randomly selected incorrect tile
    def request_hint(self):
        if self.solved or self.hints_left <= 0:
            return None
        wrong = [i for i in range(len(self._slots)) if not self.is_correct(i)]
        position = random.choice(wrong)
        self._hint = (position, self._slots[position].home_index)
        self._hints_used += 1
        return self._hint

    # automatically resets all tiles to their correct home order and upright state
    def solve(self):
        self._slots.sort(key=lambda tile: tile.home_index)
        for tile in self._slots:
            tile.reset_orientation()
        self._moves = 0
        self._hint = None

    # combines and renders all individual tile image arrays into a single full board image
    def render(self):
        rendered = [tile.render() for tile in self._slots]
        n = self._size
        rows = [np.hstack(rendered[r * n:(r + 1) * n]) for r in range(n)]
        return np.vstack(rows)
