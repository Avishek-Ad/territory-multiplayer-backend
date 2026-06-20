from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from .services import TokenService

User = get_user_model()

class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        
        # checking header format
        try:
            auth_type, token = auth_header.split(' ')
            if auth_type.lower() != 'bearer':
                return None
        except ValueError:
            raise AuthenticationFailed('Invalid authorization header format.')
        
        # decoding token and varifying user
        try:
            payload = TokenService.decode_token(token)
            if payload.get('token_type') != 'access':
                raise AuthenticationFailed('Invalid token type. Expected access token.')
            user = User.objects.get(id=payload['user_id'])
            return (user, token)
        except User.DoesNotExist:
            raise AuthenticationFailed('User not Found.')
        except Exception as e:
            raise AuthenticationFailed(str(e))