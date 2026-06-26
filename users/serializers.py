from rest_framework import serializers
from .models import User

class UserInfoSerializer(serializers.ModelSerializer):
    # avatar = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='userprofile.avatar', read_only=True)
    class Meta:
        model = User
        fields = [
            'id',
            'name',
            'avatar'
        ]
    # def get_avatar(self, obj):
    #     if hasattr(obj, 'userprofile') and obj.userprofile.avatar:
    #         return obj.userprofile.avatar.url
    #     return None

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
    