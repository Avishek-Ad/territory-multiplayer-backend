from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Room
import json
from .room_objects import Direction
import asyncio
import helpers.game_helpers as gm_h

# : add indication for online users
# currently only for authenticated users
# : make a play anomonoyusly system as well
# : also make no room_code one for local users

rooms = {}
room_width = 20
room_height = 20
minimum_players_required = 2
speed = 1



class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print(self.scope['user'])
        self.context = {}
        self.user = self.scope['user']
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        if not self.user.is_authenticated or self.room_code is None:
            await self.close()
            return
        try:
            get_db_sync = database_sync_to_async(Room.objects.get)
            self.room = await get_db_sync(room_code=self.room_code)
        except Room.DoesNotExist:
            await self.close()
            return
        self.game_room_name = f"game_{self.room_code}"
        
        await self.channel_layer.group_add(
            self.game_room_name, self.channel_name
        )
        await self.accept()
        
        is_host = await gm_h.is_user_host(self.room, self.user)
        # if host show the connected message
        if is_host:
            await self.send(text_data=json.dumps({
                "type": "JOIN_SUCCESS",
            }))
        print(is_host, self.room_code not in rooms)
        if is_host and self.room_code not in rooms:
            player = gm_h.get_initial_player_dict(name=self.user.name, width=room_width, height=room_height)
            # create the room object
            room = {
                "players": {
                    f'user-{self.user.id}': player
                },
                "trails": {
                    f'user-{self.user.id}': [(player["x"], player['y'])]
                },
                'territory_grid': [[0 for _ in range(room_height)] for _ in range(room_width)],
                'timer': 0.25*60
            }
            
            rooms[self.room_code] = room
            # TODO when somebody joins the room or leaves broadcast player info
            player_ids = [int(x.split('-')[1]) for x in rooms[self.room_code]['players'].keys()]
            users_info = await gm_h.get_user_info_from_list_of_user_id(player_ids)
            await self.send(text_data=json.dumps({
                "type": "PLAYERS",
                "players": users_info
            }))
        
        # if user not in room players send show_join message
        if f"user-{self.user.id}" not in rooms[self.room_code]['players']:
            await self.send(text_data=json.dumps({
                "type": "SHOW_JOIN",
            }))
        else:
            await self.send(text_data=json.dumps({
                "type": "JOIN_SUCCESS",
            }))
            player_ids = [int(x.split('-')[1]) for x in rooms[self.room_code]['players'].keys()]
            users_info = await gm_h.get_user_info_from_list_of_user_id(player_ids)
            await self.send(text_data=json.dumps({
                "type": "PLAYERS",
                "players": users_info
            }))
        
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
        data = json.loads(text_data)
        
        if data['type'] == "JOIN_ROOM":
            room_member = await gm_h.create_room_member(self.room, self.user)
            self.context['membership'] = room_member
            player = gm_h.get_initial_player_dict(name=self.user.name, width=room_width, height=room_height)
            rooms[self.room_code]["players"][f'user-{self.user.id}'] = player
            rooms[self.room_code]["trails"][f'user-{self.user.id}'] = [(player['x'], player['y'])]
            await self.channel_layer.group_send(
                self.game_room_name,
                {
                    "type": 'status.message',
                    "message": f"{self.user.name} has Joined the room!"
                }
            )
            await self.send(text_data=json.dumps({
                "type": "JOIN_SUCCESS",
            }))
            # TODO when somebody joins the room or leaves broadcast player info
            player_ids = [int(x.split('-')[1]) for x in rooms[self.room_code]['players'].keys()]
            users_info = await gm_h.get_user_info_from_list_of_user_id(player_ids)
            await self.channel_layer.group_send(
            self.game_room_name,
            {
                "type": 'player.list.broadcast',
                "players": users_info
            }
        )
        
        elif data['type'] == "LEAVE_ROOM":
            
            if not await gm_h.is_user_in_room(self.room, self.user):
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "ERROR", 
                            'message': "You are not in the room"
                        }
                    )
                )
            rooms[self.room_code]["players"].pop(f'user-{self.user.id}')
            rooms[self.room_code]["trails"].pop(f'user-{self.user.id}')
            # OTHER PLAYERS CAN CLAIM IT LATER
            # for row in range(len(rooms[self.room_code]['territory_grid'])):
            #     for col in range(len(rooms[self.room_code]['territory_grid'][0])):
            #         if rooms[self.room_code]['territory_grid'][row][col] == self.user.id:
            #             rooms[self.room_code]['territory_grid'][row][col] = 0
            await gm_h.remove_user_from_room(self.room, self.user)
            # send room left successfully
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "ROOM_LEAVE_SUCCESS", 
                        'message': "You are not in the room"
                    }
                )
            )
            await self.channel_layer.group_send(
                self.game_room_name,
                {
                    "type": 'status.message',
                    "message": f"{self.user.name} has left the room!"
                }
            )
            # TODO when somebody joins the room or leaves broadcast player info
            player_ids = [int(x.split('-')[1]) for x in rooms[self.room_code]['players'].keys()]
            users_info = await gm_h.get_user_info_from_list_of_user_id(player_ids)
            await self.channel_layer.group_send(
                self.game_room_name,
                {
                    "type": 'player.list.broadcast',
                    "players": users_info
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
        
        elif data['type'] == "CANCEL_GAME":
            pass
            
        elif data['type'] == "START_GAME":
            # only by host
            if not await gm_h.is_user_host(self.room, self.user):
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "ERROR", 
                            'message': "You are not in the room"
                        }
                    )
                )
                return
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
                return
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
                return
            # create the match record in the database
            await gm_h.create_match_record(self.room, room_width, room_height)
            # send a game start broadcast
            await self.channel_layer.group_send(
                self.game_room_name, 
                {
                    'type': "game.start.broadcast",
                }
            )
            # start the game loop
            self.loop_task = asyncio.create_task(self.start_game_loop())
        
        elif data['type'] == "CHANGE_DIRECTION":
            print(data)
            if data['direction'] == "up":
                rooms[self.room_code]["players"][f'user-{self.user.id}']['direction'] = Direction.UP.value
            elif data['direction'] == "down":
                rooms[self.room_code]["players"][f'user-{self.user.id}']['direction'] = Direction.DOWN.value
            elif data['direction'] == "left":
                rooms[self.room_code]["players"][f'user-{self.user.id}']['direction'] = Direction.LEFT.value
            elif data['direction'] == "right":
                rooms[self.room_code]["players"][f'user-{self.user.id}']['direction'] = Direction.RIGHT.value
        
        elif data['type'] == "PRINT":
            print(data)
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
        await self.send(text_data=json.dumps({
            "type": "GAME_STARTED",
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
    
    async def player_list_broadcast(self, event):
        players = event['players']
        await self.send(text_data=json.dumps({
            "type": "PLAYERS",
            "players": players
        }))
    
    async def player_will_respwan_broadcast(self, event):
        player_id = event['player_id']
        delay_seconds = event['delay_seconds']
        await self.send(text_data=json.dumps({
            "type": "WILL_RESPAWN",
            "message": f'Respawn in {delay_seconds}seconds',
            "player_id": player_id
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
                        'type': "game.state.broadcast",
                        'room_code': self.room_code
                    }
                )
                # reduce timer
                rooms[self.room_code]['timer'] -= 1
                
                await asyncio.sleep(1) # 300ms -> 1sec = 1000ms
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
            prev_pos = (player.get('x'), player.get('y'))
            direction = player['direction']
            if direction == Direction.UP.value:
                player['y'] -= speed
                if player['y'] < 0:
                    player['y'] = 0
            elif direction == Direction.DOWN.value:
                player['y'] += speed
                if player['y'] > room_height-1:
                    player['y'] = room_height-1
            elif direction == Direction.LEFT.value:
                player['x'] -= speed
                if player['x'] < 0:
                    player['x'] = 0
            elif direction == Direction.RIGHT.value:
                player['x'] += speed
                if player['x'] > room_width-1:
                    player['x'] = room_width-1
            
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
                    if prev_pos != (x,y):
                        # what if current position is already in the trail -> put enclosure in self territory
                        trails = rooms[self.room_code]['trails'][id]
                        gm_h.flood_filed_territory_capture(rooms[self.room_code]['territory_grid'], user_id, trails)
                        # clearing the trails
                        rooms[self.room_code]['trails'][id] = []
                    
    
    async def check_collision(self):
        # checking trial collision with other player position
        for id_p, player in rooms[self.room_code]['players'].items():
            if not player['alive']:
                continue
            x = player['x']
            y = player['y']
            for id_tp, values in rooms[self.room_code]['trails'].items():
                if id_p != id_tp and (x, y) in values:
                    # kill id_tp player as its trail was cut
                    rooms[self.room_code]['players'][id_tp]['alive'] = False 
                    rooms[self.room_code]['players'][id_tp]['deaths'] += 1
                    rooms[self.room_code]['players'][id_p]['kills'] += 1
                    # send a player has died broadcast -> after this self will show Responing in few second
                    player_killed = await gm_h.get_player_name_by_id(int(id_tp.split('-')[1]))
                    player_by = await gm_h.get_player_name_by_id(int(id_p.split('-')[1]))
                    # will respone the player after few second in random position
                    asyncio.create_task(self.handle_respwan(delay_seconds=3, player_key=id_tp))
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
                    if gm_h.player_count(rooms[self.room_code]['players'].values()) <= 1:
                        # stop the game loop and finish the match and save match records and declare winner as none
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
                # put all coordinate inside the enclosure in the territory as user_id
                trails = rooms[self.room_code]['trails'][id]
                gm_h.flood_filed_territory_capture(rooms[self.room_code]['territory_grid'], user_id, trails)
                # now remove the trails
                rooms[self.room_code]['trails'][id] = []
            # if (x, y) in rooms[self.room_code]['trails'][id]:
            #     # what if current position is already in the trail -> put enclosure in self territory
            #         trails = rooms[self.room_code]['trails'][id]
            #         gm_h.flood_filed_territory_capture(rooms[self.room_code]['territory_grid'], user_id, trails)
            #         # clearing the trails
            #         rooms[self.room_code]['trails'][id] = []
                
            
    async def stop_gameloop_and_send_game_finish_broadcast(self):
        if hasattr(self, 'loop_task'):
            self.loop_task.cancel()
        print("GAME_FINISH")
            
        # update the database and calculate the winner -> save match records and finish the match
        winner = await gm_h.finish_match_and_save_match_records_and_return_winner(self.room_code, rooms[self.room_code])
        
        print("WINNER", winner)
        await self.channel_layer.group_send(
            self.game_room_name,
            {
                'type': "game.finish.broadcast",
                'room_code': self.room_code,
                'winner': getattr(winner, "name", "")
            }
        )
        
    async def handle_respwan(self, delay_seconds: int, player_key:str):
        # send a self.send with will respone in delay_seconds
        print("IN HANDLE RESPWAN")
        player_id = int(player_key.split('-')[1])
        await self.channel_layer.group_send(
            self.game_room_name,
            {
                'type': "player.will.respwan.broadcast",
                "delay_seconds": delay_seconds,
                "player_id": player_id
            }
        )
        
        # randomize the position and reset the trails and territory
        new_x, new_y = gm_h.get_random_coordinate(room_width, room_height)
        
        rooms[self.room_code]['players'][player_key]['x'] = new_x
        rooms[self.room_code]['players'][player_key]['y'] = new_y
        rooms[self.room_code]['trails'][player_key] = [(new_x, new_y)]
        for row in range(len(rooms[self.room_code]['territory_grid'])):
            for col in range(len(rooms[self.room_code]['territory_grid'][0])):
                if rooms[self.room_code]['territory_grid'][row][col] == player_id:
                    rooms[self.room_code]['territory_grid'][row][col] = 0
        
        # wait for few seconds
        await asyncio.sleep(delay_seconds)
        
        # make the player alive
        rooms[self.room_code]['players'][player_key]['alive'] = True