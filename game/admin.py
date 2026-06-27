from django.contrib import admin
from .models import Room, RoomMember, Match, MatchResult

admin.site.register(Match)
admin.site.register(MatchResult)

class RoomMemberInline(admin.TabularInline):
    model = RoomMember
    extra = 1
    fields = [
        'user',
        'is_host'
    ]
    
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["room_code"]
    readonly_fields = ["room_code"]
    inlines = [RoomMemberInline]