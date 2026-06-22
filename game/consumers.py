from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Room, RoomMember
import json

# TODO: add indication for online users

@database_sync_to_async
def is_user_in_room(room, user):
    return RoomMember.objects.filter(room=room, user=user).exists()

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(self.scope['user'])
        self.user = self.scope['user']
        room_code = self.scope["url_route"]["kwargs"]["room_code"]
        # currently only for authenticated users
        # TODO: make a play anomonoyusly system as well
        # TODO: also make no room_code one for local users
        if self.user is AnonymousUser() or room_code is None:
            print(1)
            await self.close()
        try:
            self.room = database_sync_to_async(Room.objects.get)(room_code=room_code)
        except Room.DoesNotExist:
            print(11)
            await self.close()
        if not is_user_in_room(self.room, self.user):
            await self.close()
        self.game_room_name = f"game_{room_code}"
        
        await self.channel_layer.group_add(
            self.game_room_name, self.channel_name
        )
        await self.accept()
        
        await self.channel_layer.group_send(
            self.game_room_name,
            {
                "type": 'status.message',
                "message": f"{self.user.name} has Joined the room!"
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
                "message": f"{self.user.name} has left the room!"
            }
        )
    
    def receive(self, text_data = None, bytes_data = None):
        return super().receive(text_data, bytes_data)
    
    
    async def status_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({'message': message}))