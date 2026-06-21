from django.contrib import admin
from .models import Room, RoomMember, Match, MatchResult

admin.site.register(Room)
admin.site.register(RoomMember)