from django.db import models

class RoomStatus(models.TextChoices):
    pass

class Room(models.model):
    room_code = models.CharField(max_length=100)
    name = models.CharField(max_length=50)
    max_players = models.PositiveIntegerField(default=5)
    is_private = models.BooleanField(default=False)
    # status
    # created_at