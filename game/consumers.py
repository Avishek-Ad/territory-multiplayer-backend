from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Room, RoomMember
import json
from .room_objects import Direction
import asyncio
import helpers.game_helpers as gm_h

# : add indication for online users
# currently only for authenticated users
# : make a play anomonoyusly system as well
# : also make no room_code one for local users

rooms = {}
room_width = 200
room_height = 200
minimum_players_required = 2
speed = 1



class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(self.scope['user'])
        self.context = {}
        self.user = self.scope['user']
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        if self.user is AnonymousUser() or self.room_code is None:
            await self.close()
        try:
            self.room = database_sync_to_async(Room.objects.get)(room_code=self.room_code)
        except Room.DoesNotExist:
            await self.close()
        self.game_room_name = f"game_{self.room_code}"
        
        await self.channel_layer.group_add(
            self.game_room_name, self.channel_name
        )
        await self.accept()
        
        if gm_h.is_user_host(self.room, self.user) and not rooms[self.room_code]:
            player = gm_h.get_initial_player_dict(name=self.user.name, width=room_width, height=room_height)
            # create the room object
            room = {
                "players": {
                    f'user-{self.user.id}': player
                },
                "trails": {
                    f'user-{self.user.id}': [(player["x"], player['y'])]
                },
                'territory_grid': [0 for _ in room_height for _ in room_width],
                'timer': 5*60
            }
            
            rooms[self.room_code] = room
        
        await self.channel_layer.group_send(
            self.game_room_name,
            {
                "type": 'status.message',
                "message": f"{self.user.name} is Online"
            }
        )
    
    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            self.game_room_name, self.channel_name
        )
        
        await self.channel_layer.group_send(
            self.game_room_name,
            {
                "type": 'status.message',
                "message": f"{self.user.name} has gone Offline"
            }
        )
    
    async def receive(self, text_data):        
        data = json.load(text_data)
        
        if data['type'] == "JOIN_ROOM":
            room_member = database_sync_to_async(RoomMember.objects.get_or_create(
                room=self.room,
                user=self.user
            ))
            self.context['membership'] = room_member
            player = gm_h.get_initial_player_dict(name=self.user.name, width=room_width, height=room_height)
            rooms[self.room_code]["players"][f'user-{self.user.id}'] = player
            rooms[self.room_code]["trails"][f'user-{self.user.id}'].append((player['x'], player['y']))
            await self.channel_layer.group_send(
                self.game_room_name,
                {
                    "type": 'status.message',
                    "message": f"{self.user.name} has Joined the room!"
                }
            )
        
        elif data['type'] == "LEAVE_ROOM":
            if not gm_h.is_user_in_room(self.room, self.user):
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "ERROR", 
                            'message': "You are not in the room"
                        }
                    )
                )
            rooms[self.room_code]["players"][f'user-{self.user.id}']['alive'] = False
            gm_h.remove_user_from_room(self.room, self.user)
            await self.channel_layer.group_send(
                self.game_room_name,
                {
                    "type": 'status.message',
                    "message": f"{self.user.name} has left the room!"
                }
            )
        
        elif data['type'] == "READY": # will do later
            # only by non host
            # add a ready field in the players dictionary
            rooms[self.room_code]["players"][f'user-{self.user.id}']['ready'] = True
            
        elif data['type'] == "UNREADY": # will do later
            # only by non host
            # add a ready field in the players dictionary
            rooms[self.room_code]["players"][f'user-{self.user.id}']['ready'] = False
            
        elif data['type'] == "START_GAME":
            # only by host
            if not gm_h.is_user_host(self.room, self.user):
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "ERROR", 
                            'message': "You are not in the room"
                        }
                    )
                )
            # are minimum number of players there
            current_player_count = len(rooms[self.room_code]["players"])
            if current_player_count < minimum_players_required:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "ERROR",
                            'message': f'At minimum {minimum_players_required} players are required to start the game'
                        }
                    )
                )
            # are all available players ready
            if not gm_h.are_all_players_in_room_ready(rooms[self.room_code]['players']):
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "ERROR",
                            'message': 'Not all players are ready'
                        }
                    )
                )
            # create the match record in the database
            gm_h.create_match_record(self.room, room_width, room_height)
            # send a game start broadcast
            await self.channel_layer.group_send(
                self.game_room_name, 
                {
                    'type': "game.start.broadcast",
                    'room_code': self.room_code
                }
            )
            # start the game loop
            self.loop_task = asyncio.create_task(self.start_game_loop())
        elif data['type'] == "CHANGE_DIRECTION":
            pass
        
        """
        sending types
        GAME_STATE
        GAME_STARTED
        PLAYER_ELIMINATED
        GAME_FINISHED
        """
        
    async def status_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({ "type": "INFO", 'message': message}))
    
    async def game_start_broadcast(self, event):
        room_code = event['room_code']
        await self.send(text_data=json.dumps({
            "type": "GAME_STARTED",
            "room": rooms[room_code]
        }))
        
    async def game_finish_broadcast(self, event):
        winner = event['winner']
        await self.send(text_data=json.dumps({
            "type": "GAME_FINISHED",
            "winner": winner
        }))
        
    async def game_state_broadcast(self, event):
        room_code = event['room_code']
        await self.send(text_data=json.dumps({
            "type": "GAME_STATE",
            "room": rooms[room_code]
        }))
        
    async def player_death_broadcast(self, event):
        player_killed = event['player_killed']
        player_by = event['player_by']
        killed_player_id = event['killed_player_id']
        await self.send(text_data=json.dumps({
            "type": "PLAYER_ELIMINATED",
            "message": f'{player_killed} was killed by {player_by}',
            "killed_player": f'user-{killed_player_id}'
        }))
    
    
    async def start_game_loop(self):
        try:                    
            while rooms[self.room_code]['timer'] > 0:
                # update position
                await self.update_position()
                # check collision
                await self.check_collision()
                # update territory
                await self.update_territory()
                # broadcast GAME_STATE
                await self.channel_layer.group_send(
                    self.game_room_name, 
                    {
                        'type': "game.start.broadcast",
                        'room_code': self.room_code
                    }
                )
                # reduce timer
                rooms[self.room_code]['timer'] -= 1
                
                await asyncio.sleep(0.3) # 300ms -> 1sec = 1000ms
            else:
                # if timer is zero send a game finished broadcast and stop game loop
                await self.stop_gameloop_and_send_game_finish_broadcast()
                
        except asyncio.CancelledError:
            pass
        
    async def update_position(self):
        for player in rooms[self.room_code]['players'].values():
        # if player is not alive donot update the position
            if not player['alive']:
                continue
            if player['direction'] == Direction.UP:
                player['y'] -= speed
                if player['y'] < 0:
                    player['y'] = 0
            elif player['direction'] == Direction.DOWN:
                player['y'] += speed
                if player['y'] > room_height:
                    player['y'] = room_height
            elif player['direction'] == Direction.LEFT:
                player['x'] -= speed
                if player['x'] < 0:
                    player['x'] = 0
            elif player['direction'] == Direction.RIGHT:
                player['x'] += speed
                if player['x'] > room_width:
                    player['x'] = room_width
            
        # if current position is not in personal territory add it to the trail
        for id, values in rooms[self.room_code]['trails'].items():
            # if player is not alive donot try to create trails
            if not rooms[self.room_code]['players'][id]['alive']:
                continue
            x = rooms[self.room_code]['players'][id]['x']
            y = rooms[self.room_code]['players'][id]['y']
            user_id = int(id.split('-')[1])
            if rooms[self.room_code]['territory_grid'][x][y] != user_id:
                # what if someone else's territory turn to neutral
                rooms[self.room_code]['territory_grid'][x][y] = 0
                # what if someone else's trail -- will be checked bellow in check-collision
                # add this position to trail
                if (x, y) not in values:
                    rooms[self.room_code]['trails'][id].append((x,y))
                else:
                    # TODO what if current position is already in the trail -> put enclosure in self territory
                    pass
                    
    
    async def check_collision(self):
        # checking trial collision with other player position
        for id_p, player in rooms[self.room_code]['players'].items():
            x = player['x']
            y = player['y']
            for id_tp, values in rooms[self.room_code]['trails'].items():
                if id_p != id_tp and (x, y) in values:
                    # kill id_tp player as its trail was cut
                    rooms[self.room_code]['players'][id_tp]['alive'] = False 
                    rooms[self.room_code]['players'][id_tp]['deaths'] += 1
                    rooms[self.room_code]['players'][id_p]['kills'] += 1
                    # send a player has died broadcast -> after this self will show Responing in few second
                    player_killed = gm_h.get_player_name_by_id(int(id_tp.split('-')[1]))
                    player_by = gm_h.get_player_name_by_id(int(id_p.split('-')[1]))
                    # will respone the player after few second in random position
                    asyncio.create_task(self.handle_respwan(dely_seconds=3), player_id=player_killed)
                    await self.channel_layer.group_send(
                        self.game_room_name, 
                        {
                            'type': "player.death.broadcast",
                            'player_killed': player_killed,
                            'player_by': player_by,
                            'killed_player_id': int(id_tp.split('-')[1])
                        }
                    )
                    # if only one player alive send a game finished broadcast and stop the game loop
                    if gm_h.alive_player_count(rooms[self.room_code]['players'].values()) <= 1:
                        # TODO stop the game loop and finish the match and save match records and declare winner as none
                        await self.stop_gameloop_and_send_game_finish_broadcast() # winner will be calculated inside
                        # pass
                    # elif gm_h.alive_player_count(rooms[self.room_code]['players'].values()) == 1:
                        # stop the game loop and finish the match and save match records and declare winner as the one alive
                        # await self.stop_gameloop_and_send_game_finish_broadcast() # winner will be calculated inside
                        # pass
    
    async def update_territory(self):
        # if previous position was a trail and current is in self territory include the inclusure in territory
        for id, player in rooms[self.room_code]['players'].items():
            x = player['x']
            y = player['y']
            x_prev, y_prev = gm_h.get_player_previous_coordinate(x, y, player['direction'], speed)
            user_id = int(id.split('-')[1])
            # if prev was a trail and current is in self territory
            if (x_prev, y_prev) in rooms[self.room_code]['trails'][id] and rooms[self.room_code]['territory_grid'][x][y] == user_id:
                # TODO put all coordinate inside the enclosure in the territory as user_id
                pass
            
    async def stop_gameloop_and_send_game_finish_broadcast(self):
        if hasattr(self, 'loop_task'):
            self.loop_task.cancel()
            
        # TODO update the database and calculate the winner -> save match records and finish the match
        winner = None
                    
        await self.channel_layer.group_send(
            self.game_room_name, 
            {
                'type': "game.finish.broadcast",
                'room_code': self.room_code,
                'winner': winner
            }
        )
        
    async def handle_respwan(self, delay_seconds: int, player_id:int):
        # send a self.send with will respone in delay_seconds
        await self.send(text_data=json.dumps({
            "type": "WILL_RESPAWN",
            "message": f'Respawn in {delay_seconds}',
        }))
        
        # randomize the position and reset the trails and territory
        new_x, new_y = gm_h.get_random_coordinate(room_width, room_height)
        
        rooms[self.room_code]['players'][player_id]['x'] = new_x
        rooms[self.room_code]['players'][player_id]['y'] = new_y
        rooms[self.room_code]['trails'][player_id] = [(new_x, new_y)]
        for row in rooms[self.room_code]['territory_grid']:
            for col in row:
                if rooms[self.room_code]['territory_grid'][row][col] == player_id:
                    rooms[self.room_code]['territory_grid'][row][col] == 0
        
        # wait for few seconds
        await asyncio.sleep(delay_seconds)
        
        # make the player alive
        rooms[self.room_code]['players'][player_id]['alive'] = True