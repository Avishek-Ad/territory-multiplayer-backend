from rest_framework import serializers
from .models import Room, RoomMember

class RoomMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomMember
        fields = [
            'room',
            'user',
            'joined_at',
            'is_host'
        ]

class RoomMemberInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomMember
        fields = [
            'user',
            'joined_at',
            'is_host'
        ]

class RoomSerializer(serializers.ModelSerializer):
    room_members = RoomMemberInlineSerializer(source="members", read_only=True, many=True)
    class Meta:
        model = Room
        fields = [
            'room_code',
            'name',
            'max_players',
            'room_members',
            'is_private',
            'status',
            'created_at'
        ]
        
class RoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            'name',
            'is_private',
        ]