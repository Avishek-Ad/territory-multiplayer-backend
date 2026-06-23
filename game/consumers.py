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
            # TODO send a game start broadcast
            await self.channel_layer.group_send(
                self.game_room_name, 
                {
                    'type': "game.start.broadcast",
                    'room_code': self.room_code
                }
            )
            # TODO start the game loop
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
            "type": "GAME_START",
            "room": rooms[room_code]
        }))
        
    async def game_state_broadcast(self, event):
        room_code = event['room_code']
        await self.send(text_data=json.dumps({
            "type": "GAME_STATE",
            "room": rooms[room_code]
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
                # TODO broadcast GAME_STATE
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
        except asyncio.CancelledError:
            pass
        
    async def update_position(self):
        for player in rooms[self.room_code]['players'].values():
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
            x = rooms[self.room_code]['players'][id]['x']
            y = rooms[self.room_code]['players'][id]['y']
            user_id = int(id.split('-')[1])
            if rooms[self.room_code]['territory_grid'][x][y] != user_id:
                # what if someone else's territory turn to neutral
                rooms[self.room_code]['territory_grid'][x][y] = 0
                # what if someone else's trail -- will be checked bellow in check-collision
                # add this position to trail
                # what if current position is already in the trail
                if (x, y) not in values:
                    rooms[self.room_code]['trails'][id].append((x,y))
                    
    
    async def check_collision(self):
        # checking trial collision with other player position
        for id_p, player in rooms[self.room_code]['players'].items():
            x = player['x']
            y = player['y']
            for id_tp, values in rooms[self.room_code]['trails'].items():
                if id_p != id_tp and (x, y) in values:
                    # kill id_tp player as its trail was cut
                    rooms[self.room_code]['players'][id_tp]['alive'] = False
    
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