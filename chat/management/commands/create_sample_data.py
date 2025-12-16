from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from chat.models import ChatRoom

class Command(BaseCommand):
    help = 'Create sample users and chat rooms for testing'

    def handle(self, *args, **kwargs):
        # Create sample users
        users = [
            {'username': 'alice', 'password': 'password123'},
            {'username': 'bob', 'password': 'password123'},
            {'username': 'charlie', 'password': 'password123'},
        ]

        for user_data in users:
            user, created = User.objects.get_or_create(username=user_data['username'])
            if created:
                user.set_password(user_data['password'])
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created user: {user.username}"))

        # Create sample group chat rooms
        group_rooms = [
            {'name': 'General Chat'},
            {'name': 'Django Developers'},
            {'name': 'Random Topics'},
        ]

        for room_data in group_rooms:
            room, created = ChatRoom.objects.get_or_create(name=room_data['name'], type='group')
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created chat room: {room.name}"))

        self.stdout.write(self.style.SUCCESS("Sample data created successfully!"))