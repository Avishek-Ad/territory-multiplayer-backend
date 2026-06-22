from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Room, RoomMember
import json
from .room_objects import User, Room, Direction
import random

# TODO: add indication for online users
# currently only for authenticated users
# TODO: make a play anomonoyusly system as well
# TODO: also make no room_code one for local users

rooms = {}
room_width = 200
room_height = 200
minimum_players_required = 2

@database_sync_to_async
def is_user_host(room, user):
    return RoomMember.objects.filter(room=room, user=user, is_host=True).exists()

@database_sync_to_async
def is_user_in_room(room, user):
    return RoomMember.objects.filter(room=room, user=user).exists()

@database_sync_to_async
def remove_user_from_room(room, user):
    RoomMember.objects.get(room=room, user=user).delete()
    
def get_initial_player_dict():
    return {
        'x': random.randint(0, room_width),
        'y': random.randint(0, room_height),
        'direction': random.choice(list(Direction)),
        'alive': True,
        'ready': True
    }

def are_all_players_in_room_ready(room_code):
    pass

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
        
        if is_user_host(self.room, self.user) and not rooms[self.room_code]:
            player = get_initial_player_dict()
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
            player = get_initial_player_dict()
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
            if not is_user_in_room(self.room, self.user):
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "ERROR", 
                            'message': "You are not in the room"
                        }
                    )
                )
            rooms[self.room_code]["players"][f'user-{self.user.id}']['alive'] = False
            remove_user_from_room(self.room, self.user)
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
            if not is_user_host(self.room, self.user):
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
            pass
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