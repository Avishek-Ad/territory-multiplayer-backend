from django.urls import path
from . import views

urlpatterns = [
    path('', views.RoomListCreateAPIView.as_view()),
    path('<str:room_code>/', views.RoomRetriveUpdateAPIView.as_view()),
    # path('<str:room_code>/join/', views.RoomJoinAPIView.as_view()),
    # path('<str:room_code>/leave/', views.RoomLeaveAPIView.as_view()),
    # join and leave will be handled by the websocket
    
    path('<str:room_code>/is_host/', views.IsUserHost.as_view()),
    path('<str:room_code>/match_stats/<int:match_id>/', views.GetMatchStats.as_view())
]
