from django.urls import path
from chat import views as chat_views

urlpatterns = [
    path("", chat_views.chatPage, name="chatPage"),
    path("login/", chat_views.loginPage, name="loginUser"),
    path("logout/", chat_views.logoutUser, name="logoutUser"),
    path("group/<str:room_name>/", chat_views.groupRoomPage, name="groupRoomPage"),
    path("private/<str:username>/", chat_views.privateRoomPage, name="privateRoomPage"),
]