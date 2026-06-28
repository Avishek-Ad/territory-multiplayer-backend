from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework import permissions
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from .services import TokenService
from django.contrib.auth import get_user_model
from users.serializers import UserRegisterSerializer, UserInfoSerializer

User = get_user_model()

class RetriveUserStatsView(APIView):
    pass

class RetriveUserInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        serializer = UserInfoSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = TokenService.generate_token_pair(user)
            return Response(token, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            

class TokenObtainView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
            
        user = authenticate(email=email, password=password)
        if user is not None:
            # remove all previous refresh token for this user
            has_previous_token = TokenService.has_refresh_token(user)
            if has_previous_token:
                TokenService.remove_user_refresh_tokens(user)
            
            token = TokenService.generate_token_pair(user)
            return Response(token, status=status.HTTP_200_OK)
        
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({'detail': 'Refresh token required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_token_in_db = TokenService.verify_refresh_token_in_db(refresh_token)
        if not is_token_in_db:
            return Response({'detail': 'Refresh token not found.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            payload = TokenService.decode_token(refresh_token)
            if payload.get('token_type') != 'refresh':
                return Response({'detail': 'Invalid token type.'}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.get(id=payload['user_id'])
            
            # the current refreshtoken will be removed from db and the new one will be added
            new_tokens = TokenService.generate_token_pair(user, old_refresh=refresh_token)
            return Response (new_tokens, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        
class TokenRemoveView(APIView):
    
    def post(self, request):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({'detail': 'Refresh token required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_token_in_db = TokenService.verify_refresh_token_in_db(refresh_token)
        if not is_token_in_db:
            return Response({'detail': 'Refresh token not found.'}, status=status.HTTP_400_BAD_REQUEST)
        
        TokenService.remove_refresh_token(refresh_token)
        return Response ({'detail': 'Logout successful'}, status=status.HTTP_200_OK)