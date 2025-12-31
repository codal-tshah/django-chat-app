from django.urls import path
from chat.consumers import ChatConsumer

# Updated WebSocket routing to handle multiple chat rooms by including a room name in the URL.
websocket_urlpatterns = [
    path("ws/chat/private/<str:room_name>/", ChatConsumer.as_asgi(), name="private_chat"),
    path("ws/chat/group/<str:room_name>/", ChatConsumer.as_asgi(), name="group_chat"),
    path("ws/chat/lobby/", ChatConsumer.as_asgi(), name="lobby"), # Re-using ChatConsumer for simplicity, but treating 'lobby' as a room
]