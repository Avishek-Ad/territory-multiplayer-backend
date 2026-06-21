from django.urls import path
from . import views

urlpatterns = [
    path('', views.RoomListCreateAPIView.as_view()),
    path('<str:room_code>/', views.RoomRetriveUpdateAPIView.as_view()),
    path('<str:room_code>/join/', views.RoomJoinAPIView.as_view()),
    path('<str:room_code>/leave/', views.RoomLeaveAPIView.as_view()),
]
