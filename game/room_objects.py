from typing import TypedDict
from enum import Enum

class Direction(Enum):
    UP = "up"
    DOWN = 'down'
    LEFT = 'left'
    RIGHT = 'right'

class User(TypedDict):
    x: int
    y: int
    direction: Direction
    alive: bool
    
class Room(TypedDict):
    players: list[User]
    trails: dict[str, list[tuple[int, int]]]
    territory_grid: list[list[(int, int)]]
    timer: int
