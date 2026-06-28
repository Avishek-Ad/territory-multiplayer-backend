from rest_framework import serializers
from .models import Room, RoomMember, MatchResult
from django.conf import settings

class MatchResultSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = MatchResult
        fields = [
            'user_id',
            'name',
            'avatar',
            'kills',
            'deaths',
            'territory_percentage',
            'rank'
        ]
        
    def get_user_id(self, obj):
        return obj.user.id
    
    def get_name(self, obj):
        return obj.user.name
    
    def get_avatar(self, obj):
        avatar_url = ""
        base_url = settings.BACKEND_BASE_URL.rstrip('/')
        if hasattr(obj.user, 'userprofile') and obj.user.userprofile.avatar:
            avatar_url = f"{base_url}{obj.user.userprofile.avatar.url}"
        return avatar_url

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
    room_code = serializers.SerializerMethodField(read_only=True)
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
    
    def get_room_code(self, obj):
        return obj.room_code
        
class RoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            'name',
            'is_private',
        ]