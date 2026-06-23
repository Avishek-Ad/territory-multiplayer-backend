import random
from channels.db import database_sync_to_async
from game.models import RoomMember
from game.room_objects import Direction

@database_sync_to_async
def is_user_host(room, user):
    return RoomMember.objects.filter(room=room, user=user, is_host=True).exists()

@database_sync_to_async
def is_user_in_room(room, user):
    return RoomMember.objects.filter(room=room, user=user).exists()

@database_sync_to_async
def remove_user_from_room(room, user):
    RoomMember.objects.get(room=room, user=user).delete()
    
def get_initial_player_dict(name, width, height):
    return {
        'name': name,
        'x': random.randint(0, width),
        'y': random.randint(0, height),
        'direction': random.choice(list(Direction)),
        'alive': True,
        'ready': True
    }

def are_all_players_in_room_ready(players:dict):
    for player in players.values():
        if not player['ready']:
            return False
    return True

def get_player_previous_coordinate(x, y, dir, speed):
    if dir == Direction.UP:
        y -= speed
    elif dir == Direction.DOWN:
        y += speed        
    elif dir == Direction.LEFT:
        x -= speed        
    elif dir == Direction.RIGHT:
        x += speed
    return x, y