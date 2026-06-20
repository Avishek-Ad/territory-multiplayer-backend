from rest_framework import serializers
from .models import User

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
    