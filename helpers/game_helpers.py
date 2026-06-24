import random
from channels.db import database_sync_to_async
from game.models import RoomMember, Match, MatchResult, Room, MatchStatus
from game.room_objects import Direction
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_player_name_by_id(player_id):
    return User.objects.get(id=player_id).name or ""

@database_sync_to_async
def is_user_host(room, user):
    return RoomMember.objects.filter(room=room, user=user, is_host=True).exists()

@database_sync_to_async
def is_user_in_room(room, user):
    return RoomMember.objects.filter(room=room, user=user).exists()

@database_sync_to_async
def remove_user_from_room(room, user):
    RoomMember.objects.get(room=room, user=user).delete()
    
@database_sync_to_async
def create_match_record(room, width, height):
    Match.objects.create(
        room=room,
        map_width=width,
        map_height=height
    )
    
@database_sync_to_async
def finish_match_and_save_match_records_and_return_winner(room_code, room):
    ranks = calculate_rank_and_territory_percentage(room['territory_grid'])
    
    room_obj = Room.objects.get(room_code=room_code)
    match = room_obj.matches.first()
    match.status = MatchStatus.FINISHED
    match.save()
    
    player_data_map = {}
    for player_key, player in room['players'].items():
        user_id = int(player_key.split('-')[1])
        player_data_map[user_id] = player
    
    # batch user fetch O(1) db hit
    users = User.objects.in_bulk(player_data_map.keys())
    
    # prepare match result in memory
    match_records_to_create = []
    for user_id, player in player_data_map.items():
        user = users.get(user_id)
        if not user:
            continue
        rank_info = ranks.get(user_id, [0, 0.0])
        match_records_to_create.append(
            MatchResult(
                match=match,
                user=user,
                kills=player['kills'],
                deaths=player['deaths'],
                territory_percentage=rank_info[1],
                rank=rank_info[0]
            )
        )
    
    # Insert all records atomically in a single multi-row SQL operation
    if match_records_to_create:
        MatchResult.objects.bulk_create(match_records_to_create)
    
    # clear cached relationships to ensure the newly inserted data is read
    if hasattr(match, '_prefetched_objects_cache'):
        match._prefetched_objects_cache.clear()
    
    return match.winner
        
def calculate_rank_and_territory_percentage(territory_grid):
    ranks = {}
    total_area = len(territory_grid) * len(territory_grid[0])
    for row in territory_grid:
        for col in row:
            if col == 0:
                continue
            ranks[col] = ranks.get(col, 0) + 1
    
    sorted_keys = sorted(ranks, key=ranks.get, reverse=True)
    
    ranks_lookup = {id_: rank for rank, id_ in enumerate(sorted_keys, start=1)}
    
    for id_, area in ranks.items():
        ranks[id_] = [ranks_lookup[id_], area/total_area]
    
    return ranks
        
def alive_player_count(players: list) -> int:
    alive = 0
    for player in players:
        if player['alive']:
            alive += 1
    return alive
    
def get_initial_player_dict(name, width, height):
    return {
        'name': name,
        'x': random.randint(0, width),
        'y': random.randint(0, height),
        'direction': random.choice(list(Direction)),
        'alive': True,
        'ready': True,
        'kills': 0,
        'deaths': 0
    }
    
def get_random_coordinate(width, height):
    return random.randint(0, width), random.randint(0, height)

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

def flood_filed_territory_capture(territory_grid, player_id, trails):
    rows = len(territory_grid)
    cols = len(territory_grid[0])
    to_visit = [(0,0)]
    visited = [[False for _ in range(cols)] for _ in range(rows)]
    
    while to_visit:
        r, c = to_visit.pop()
        neighbors = [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]
        
        for nr, nc in neighbors:
            if nr<0 or nr>=rows or nc<0 or nc>=cols:
                continue
            if visited[nr][nc]:
                continue
            if territory_grid[nr][nc] == player_id or (nr, nc) in trails: # wall
                continue
            
            visited[nr][nc] = True
            to_visit.append((nr, nc))
        
    for r in range(rows):
        for c in range(cols):
            if not visited[r][c]:
                territory_grid[r][c] = player_id
    return territory_grid