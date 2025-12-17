import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message
from django.contrib.auth.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if 'room_name' in self.scope['url_route']['kwargs']:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
        else:
            # Fallback for lobby or other routes without room_name
            self.room_name = "lobby"
            
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Mark all messages in this room as read by this user
        read_msg_ids = await self.mark_room_read(self.room_name, self.scope["user"])
        
        if read_msg_ids:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "bulk_read",
                    "message_ids": read_msg_ids,
                    "username": self.scope["user"].username
                }
            )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type", "chat_message")
        username = data.get("username")

        if msg_type == "chat_message":
            message = data["message"]
            # Save message to database
            msg_id = await self.save_message(username, self.room_name, message)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "username": username,
                    "id": msg_id
                }
            )
            
            # If this is a private chat, send notification to the lobby
            if "private" in self.room_name:
                # Extract the other user's name from the room name (e.g., private_user1_user2)
                parts = self.room_name.split('_')
                if len(parts) >= 3:
                    # parts[0] is 'private', parts[1] and parts[2] are usernames
                    target_user = parts[2] if parts[1] == username else parts[1]
                    
                    await self.channel_layer.group_send(
                        "chat_lobby",
                        {
                            "type": "notification",
                            "sender": username,
                            "target_user": target_user
                        }
                    )
        elif msg_type == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_typing",
                    "username": username,
                    "is_typing": data.get("is_typing", True)
                }
            )
        elif msg_type == "read_receipt":
            msg_id = data.get("message_id")
            if msg_id:
                await self.mark_message_read(msg_id, username)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "message_read",
                        "message_id": msg_id,
                        "username": username
                    }
                )

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]
        username = event["username"]
        msg_id = event.get("id")

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": message,
            "username": username,
            "id": msg_id
        }))

    async def user_typing(self, event):
        username = event["username"]
        is_typing = event["is_typing"]

        await self.send(text_data=json.dumps({
            "type": "typing",
            "username": username,
            "is_typing": is_typing
        }))

    async def message_read(self, event):
        message_id = event["message_id"]
        username = event["username"]

        await self.send(text_data=json.dumps({
            "type": "read_receipt",
            "message_id": message_id,
            "username": username
        }))

    async def bulk_read(self, event):
        message_ids = event["message_ids"]
        username = event["username"]

        await self.send(text_data=json.dumps({
            "type": "bulk_read",
            "message_ids": message_ids,
            "username": username
        }))

    async def notification(self, event):
        sender = event["sender"]
        target_user = event["target_user"]

        await self.send(text_data=json.dumps({
            "type": "notification",
            "sender": sender,
            "target_user": target_user
        }))

    @database_sync_to_async
    def save_message(self, username, room_name, message_content):
        try:
            user = User.objects.get(username=username)
            room = ChatRoom.objects.get(name=room_name)
            msg = Message.objects.create(sender=user, room=room, content=message_content)
            msg.read_by.add(user) # Sender has read their own message
            return msg.id
        except Exception as e:
            print(f"Error saving message: {e}")
            return None

    @database_sync_to_async
    def mark_message_read(self, message_id, username):
        try:
            user = User.objects.get(username=username)
            message = Message.objects.get(id=message_id)
            message.read_by.add(user)
        except Exception as e:
            print(f"Error marking message read: {e}")

    @database_sync_to_async
    def mark_room_read(self, room_name, user):
        read_msg_ids = []
        try:
            room = ChatRoom.objects.get(name=room_name)
            messages = Message.objects.filter(room=room).exclude(read_by=user).exclude(sender=user)
            for msg in messages:
                msg.read_by.add(user)
                read_msg_ids.append(msg.id)
        except Exception as e:
            print(f"Error marking room read: {e}")
        return read_msg_ids