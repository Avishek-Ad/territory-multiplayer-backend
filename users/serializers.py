from rest_framework import serializers
from .models import User, UserProfile
from django.conf import settings
from game.serializers import MatchRecordInlineSerializer


class UserStatsSerializer(serializers.Serializer):
    total_matches = serializers.IntegerField(read_only=True)
    wins = serializers.IntegerField(read_only=True)
    total_kills = serializers.IntegerField(read_only=True)
    total_deaths = serializers.IntegerField(read_only=True)
    avg_territory_percentage = serializers.DecimalField(
        max_digits=6, decimal_places=4, read_only=True
    )
    match_history = MatchRecordInlineSerializer(source='matches', many=True, read_only=True)

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
    
class UserNameChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'name'
        ]
    
class ProfileImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'avatar'
        ]