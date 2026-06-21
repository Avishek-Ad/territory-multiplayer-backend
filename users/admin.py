from django.contrib import admin
from .models import User, UserProfile

# admin.site.register(User)
# admin.site.register(UserProfile)

class UserProfileInline(admin.TabularInline):
    model = UserProfile
    max_num = 1
    extra = 1
    fields = [
        'avatar',
        'rating',
        'total_matches',
        'wins'
    ]

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['name']
    inlines = [UserProfileInline]
    