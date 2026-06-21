from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import User, UserProfile

@receiver(post_save, sender=User)
def user_post_save_profile_creation(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
        )