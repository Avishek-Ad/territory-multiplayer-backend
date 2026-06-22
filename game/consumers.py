from channels.generic.websocket import AsyncWebsocketConsumer

class GameConsumer(AsyncWebsocketConsumer):
    def connect(self):
        print(self.scope['user'])
        return super().connect()
    
    def disconnect(self, code):
        return super().disconnect(code)
    
    def receive(self, text_data = None, bytes_data = None):
        return super().receive(text_data, bytes_data)