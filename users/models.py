import uuid
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from datetime import timedelta

class UserManager(BaseUserManager):
    def _create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email")
        email = self.normalize_email(email)
        name = extra_fields.pop('name', None)
        if name is None or name == "":
            name = email.split("@")[0]
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, **extra_fields)
    
    
class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    # is_superuser will come from PermissionMixin
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] 
    
    def __str__(self):
        return self.name
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    # avatar
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    # TODO: later use cloudinary image
    # rating 0 to 5
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    # total_matches
    total_matches = models.PositiveIntegerField(default=0)
    # wins
    wins = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.user}"
    
def get_refresh_token_expiry():
    return timezone.now() + timedelta(weeks=1)

class RefreshToken(models.Model):
   id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
   user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
   token = models.TextField()
   is_active = models.BooleanField(default=True)
   expires_at = models.DateTimeField(default=get_refresh_token_expiry)
   created_at = models.DateTimeField(auto_now_add=True)
   
   def __str__(self):
       return f"Token for {self.user.name} - Exp: {self.expires_at}"
    
   @property
   def has_expired(self):
       return self.expires_at >= timezone.now()