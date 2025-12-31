import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    active_connections = 0
    
    async def connect(self):
        try:
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
            
            # Track active connections
            ChatConsumer.active_connections += 1
            logger.info(f"WebSocket CONNECTED: User={self.scope['user'].username}, Room={self.room_name}, Active connections: {ChatConsumer.active_connections}")
        
        except Exception as e:
            # Log the error but don't show full stack trace for Redis connection issues
            if "redis" in str(e).lower() or "connection" in str(e).lower():
                logger.warning(f"Redis connection issue during WebSocket connect for user {self.scope['user'].username}: {type(e).__name__}")
            else:
                logger.error(f"Error in WebSocket connect: {e}")
            # Close the connection gracefully
            await self.close()

    async def disconnect(self, close_code):
        # Track active connections - only decrement if we actually connected
        if hasattr(self, 'room_group_name') and hasattr(self, 'room_name'):
            ChatConsumer.active_connections -= 1
            logger.info(f"WebSocket DISCONNECTED: User={self.scope['user'].username}, Room={self.room_name}, Code={close_code}, Active connections: {ChatConsumer.active_connections}")
            
            # Leave room group
            try:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            except Exception as e:
                # Redis might be down, just log it
                logger.debug(f"Could not leave group (Redis may be down): {e}")
        else:
            # Connection failed before setup completed
            logger.debug(f"WebSocket disconnected before full setup, Code={close_code}")

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
            
            # Send notification to the lobby
            notification_data = {
                "type": "notification",
                "sender": username,
            }
            
            if "private" in self.room_name:
                # Private Chat Logic
                parts = self.room_name.split('_')
                if len(parts) >= 3:
                    target_user = parts[2] if parts[1] == username else parts[1]
                    notification_data["target_user"] = target_user
                    notification_data["room_type"] = "private"
            else:
                # Group Chat Logic
                notification_data["room_name"] = self.room_name
                notification_data["room_type"] = "group"

            await self.channel_layer.group_send("chat_lobby", notification_data)
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
        elif msg_type == "mark_read":
            # Mark all messages in the room as read by this user
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
        # Forward the entire event data to the WebSocket
        # Remove the 'type' key from event if it conflicts or just pass it along
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, username, room_name, message_content):
        try:
            user = User.objects.get(username=username)
            # Ensure room exists (e.g. if it's a new group chat)
            # Determine type based on name convention or default to group
            room_type = "private" if room_name.startswith("private_") else "group"
            room, created = ChatRoom.objects.get_or_create(name=room_name, defaults={"type": room_type})
            
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
            # If it's the lobby, we don't have a room to mark read
            if room_name == "lobby":
                return []
                
            room = ChatRoom.objects.get(name=room_name)
            messages = Message.objects.filter(room=room).exclude(read_by=user).exclude(sender=user)
            for msg in messages:
                msg.read_by.add(user)
                read_msg_ids.append(msg.id)
        except ChatRoom.DoesNotExist:
            # Room might not exist yet if it's a new group chat being joined via URL
            # In that case, there are no messages to mark read anyway.
            pass
        except Exception as e:
            print(f"Error marking room read: {e}")
        return read_msg_ids