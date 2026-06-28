from rest_framework import serializers
from .models import User
from django.conf import settings
from game.serializers import MatchRecordInlineSerializer
from django.db.models import Sum, Count



class UserStatsSerializer(serializers.Serializer):
    total_matches = serializers.SerializerMethodField()
    wins = serializers.SerializerMethodField()
    total_kills = serializers.SerializerMethodField()
    total_deaths = serializers.SerializerMethodField()
    avg_territory_percentage = serializers.SerializerMethodField()
    # match_history = MatchRecordInlineSerializer(source=)

class UserInfoSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    # avatar = serializers.ImageField(source='userprofile.avatar', read_only=True)
    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'avatar'
        ]
    def get_avatar(self, obj):
        base_url = settings.BACKEND_BASE_URL.rstrip('/')
        if hasattr(obj, 'userprofile') and obj.userprofile.avatar:
            return f"{base_url}{obj.userprofile.avatar.url}"
        return None

class UserRegisterSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'email',
            'password',
        ]
        
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    