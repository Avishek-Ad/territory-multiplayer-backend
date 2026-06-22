import jwt
from datetime import datetime, timedelta, timezone
from django.conf  import settings
from .models import RefreshToken
from django.db import transaction

class TokenService:
    @staticmethod
    def generate_token_pair(user, old_refresh=None):
        now = datetime.now(timezone.utc)
        
        with transaction.atomic():
            if old_refresh is not None:
                RefreshToken.objects.filter(token=old_refresh).delete()
            
            access_payload = {
                'token_type': 'access',
                'user_id': str(user.id),
                'exp': now + timedelta(days=1),
                'iat': now,
            }
            
            refresh_payload = {
                'token_type': 'refresh',
                'user_id': str(user.id),
                'exp': now + timedelta(days=7),
                'iat': now,
            }
            
            access = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')
            refresh = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')
            
            RefreshToken.objects.create(token=refresh, user=user)
            
            return {
                'access': access,
                'refresh': refresh
            }
        
    @staticmethod
    def decode_token(token):
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired.")
        except jwt.InvalidTokenError:
            raise Exception("Invalid token.")
        
    @staticmethod
    def verify_refresh_token_in_db(token):
        return RefreshToken.objects.filter(token=token).exists()
    
    @staticmethod
    def remove_refresh_token(token):
        RefreshToken.objects.filter(token=token).delete()
        return
    
    @staticmethod
    def has_refresh_token(user):
        return user.tokens.all().exists()
    
    @staticmethod
    def remove_user_refresh_tokens(user):
        user.tokens.all().delete()
        return