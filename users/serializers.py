from rest_framework import serializers
from .models import User

class UserInfoSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            'name',
            'avatar'
        ]
    def get_avatar(self, obj):
        if hasattr(obj, 'userprofile'):
            return obj.userprofile.avatar if obj.userprofile.avatar else None
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
    