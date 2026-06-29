from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view()),
    path('login/', views.TokenObtainView.as_view()),
    path('logout/', views.TokenRemoveView.as_view()),
    path('refresh/', views.TokenRefreshView.as_view()),
    path('my-info/', views.RetriveUserInfoView.as_view()),
    path('stats/', views.RetriveUserStatsView.as_view()),
    path('avatar/', views.ChangeUserAvatarView.as_view()),
    path('update_username/', views.ChangeUsernameView.as_view())
]