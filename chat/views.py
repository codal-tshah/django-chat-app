from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from .models import ChatRoom, Message
import logging

logger = logging.getLogger(__name__)

def loginPage(request):
    if request.method == "POST":
        username = request.POST.get("username")
        if username:
            user, created = User.objects.get_or_create(username=username)
            login(request, user)
            return redirect("chatPage")
    return render(request, "chat/LoginPage.html")

def logoutUser(request):
    logout(request)
    return redirect("loginUser")

def chatPage(request):
    if not request.user.is_authenticated:
        return redirect("loginUser")
    
    # Show a list of public rooms or just a default one
    # For now, let's list some default rooms and allow creating new ones
    public_rooms = ChatRoom.objects.filter(type="group")
    users = User.objects.exclude(id=request.user.id)
    
    # Calculate unread counts for private chats
    for user in users:
        # Construct the private room name
        sorted_users = sorted([request.user.username, user.username])
        room_name = f"private_{sorted_users[0]}_{sorted_users[1]}"
        
        # Count messages in this room not read by current user
        unread_count = Message.objects.filter(
            room__name=room_name,
            room__type="private"
        ).exclude(read_by=request.user).count()
        
        user.unread_count = unread_count

    return render(request, "chat/landingPage.html", {
        "public_rooms": public_rooms,
        "users": users
    })

def groupRoomPage(request, room_name):
    if not request.user.is_authenticated:
        return redirect("loginUser")

    sanitized_room_name = room_name.replace(" ", "_")
    chat_room, created = ChatRoom.objects.get_or_create(name=sanitized_room_name, type="group")

    if request.user not in chat_room.participants.all():
        chat_room.participants.add(request.user)

    messages = Message.objects.filter(room=chat_room).order_by("timestamp")

    return render(request, "chat/chatPage.html", {
        "room_name": sanitized_room_name,
        "room_type": "group",
        "messages": messages,
        "current_user": request.user
    })

def privateRoomPage(request, username):
    if not request.user.is_authenticated:
        return redirect("loginUser")

    other_user = get_object_or_404(User, username=username)
    
    # Ensure consistent room name for private chat (e.g., sorted usernames)
    users = sorted([request.user.username, other_user.username])
    room_name = f"private_{users[0]}_{users[1]}"
    
    chat_room, created = ChatRoom.objects.get_or_create(name=room_name, type="private")
    
    if request.user not in chat_room.participants.all():
        chat_room.participants.add(request.user)
    if other_user not in chat_room.participants.all():
        chat_room.participants.add(other_user)

    messages = Message.objects.filter(room=chat_room).order_by("timestamp")

    return render(request, "chat/chatPage.html", {
        "room_name": room_name,
        "room_type": "private",
        "other_user": other_user,
        "messages": messages,
        "current_user": request.user
    })