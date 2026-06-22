import jwt
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from urllib.parse import parse_qs
from django.conf import settings


@database_sync_to_async
def get_user_from_payload(payload):
    User = get_user_model()
    user_id = payload.get('user_id') or payload.get('id') or payload.get('sub')
    if not user_id:
        return AnonymousUser()
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner
        
    async def __call__(self, scope, receive, send):
        query_string = parse_qs(scope['query_string'].decode())
        token = query_string.get('token', [None])[0]
        if token:
            # validating jwt token
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user = await get_user_from_payload(payload)
                scope['user'] = user
            except Exception as e:
                print(f"JWT Authentication Failed: {e}")
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
            
        return await self.inner(scope, receive, send)
    
# channel layer stack
def TokenAuthMiddlewareStack(inner):
    return TokenAuthMiddleware(AuthMiddlewareStack(inner))