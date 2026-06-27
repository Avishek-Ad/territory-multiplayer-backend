from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import RoomSerializer, RoomMemberSerializer, RoomUpdateSerializer
from .models import Room, RoomMember
from django.shortcuts import get_object_or_404
from rest_framework import status

class RoomListCreateAPIView(generics.ListCreateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    
    def perform_create(self, serializer):
        room = serializer.save()
        user = self.request.user
        RoomMember.objects.get_or_create(
            room=room,
            user=user,
            is_host=True
        )
        
class RoomRetriveUpdateAPIView(generics.RetrieveUpdateAPIView):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = "room_code"
    
    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return RoomUpdateSerializer
        return super().get_serializer_class()
    
# join room
class RoomJoinAPIView(APIView):
    def post(self, request, room_code):
        room = get_object_or_404(Room, room_code=room_code)
        user = request.user
        room_member = RoomMember.objects.get_or_create(
            room=room,
            user=user,
            is_host=False,
        )
        serializer = RoomMemberSerializer(room_member)
        return Response(serializer.data, status=status.HTTP_200_OK)

#leave room
class RoomLeaveAPIView(APIView):
    def post(self, request, room_code):
        room = get_object_or_404(Room, room_code=room_code)
        user = request.user
        room_member = get_object_or_404(room=room, user=user)
        # if the user leaving is the host destroy it
        if room_member.is_host:
            room.delete() # it will cascade delete other members
        else:
            room_member.delete()
        return Response({"message":"Room Leave Successful"}, status=status.HTTP_200_OK)
    
class IsUserHost(APIView):
    def get(self, request, room_code):
        room = get_object_or_404(Room, room_code=room_code)
        rooms_member = room.members.filter(user=request.user).first()
        if not rooms_member:
            return Response({"message": "you are not a member of this room"}, status=status.HTTP_403_FORBIDDEN)
        return Response(rooms_member.is_host, status=status.HTTP_200_OK)