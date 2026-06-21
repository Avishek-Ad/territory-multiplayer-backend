import helpers
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

User = get_user_model()

class RoomStatus(models.TextChoices):
    WAITING = "waiting", "Waiting"
    STARTING = "starting", "Starting"
    IN_PROGRESS = "in_progress", "In Progress"
    FINISHED = "finished", "Finished"

class Room(models.Model):
    room_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=50)
    max_players = models.PositiveIntegerField(
        default=5, 
        validators=[MinValueValidator(2)]
        )
    is_private = models.BooleanField(default=False)
    # status
    status = models.CharField(max_length=15, choices=RoomStatus.choices, default=RoomStatus.WAITING)
    # created_at
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.room_code}"
    
    def save(self, *args, **kwargs):
        if self.room_code == "" or self.room_code is None:
            self.room_code = helpers.generate_room_code(self)
        return super().save(*args, **kwargs)
    
class RoomMember(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="joined_rooms")
    joined_at = models.DateTimeField(auto_now_add=True)
    is_host = models.BooleanField(default=False)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user"],
                name="unique_room_member"
            )
        ]        
    
    def __str__(self):
        return f"{self.room} - {self.user}"
    
class Match(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="matches")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    winner = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name="won_matches",
        null=True,
        blank=True
        )
    map_size = models.DecimalField(max_digits=10, decimal_places=2) # will be a radius
    
class MatchResult(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="results")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="matches")
    kills = models.PositiveIntegerField(default=0)
    deaths = models.PositiveIntegerField(default=0)
    territory_percentage = models.DecimalField(max_digits=4, decimal_places=2)
    rank = models.PositiveIntegerField(default=1)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["match", "user"],
                name="unique_match_result"
            )
        ]