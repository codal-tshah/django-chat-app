from django.db import models
from django.contrib.auth.models import User

class ChatRoom(models.Model):
    ROOM_TYPES = (
        ("private", "Private"),
        ("group", "Group"),
    )

    name = models.CharField(max_length=255, unique=True, null=True, blank=True)
    type = models.CharField(max_length=10, choices=ROOM_TYPES, default="group")
    participants = models.ManyToManyField(User, related_name="chat_rooms")

    def __str__(self):
        if self.type == "private":
            return f"Private Chat ({', '.join([user.username for user in self.participants.all()])})"
        return self.name

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages", default=1)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, related_name="read_messages", blank=True)

    def __str__(self):
        return f"{self.sender}: {self.content}"