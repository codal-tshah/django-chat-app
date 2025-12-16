# django-chat-app
Using Django channels prepare a basic chat app

## Features
- **Real-time Messaging**: Powered by Django Channels and WebSockets.
- **No Authentication Required**: Simply enter a username to join.
- **Group Chats**: Create or join public rooms.
- **Private Chats**: Direct messaging with other online users.
- **Premium UI**: Dark mode design with responsive layout.
- **Message Persistence**: Chat history is saved.
- **Typing Indicators**: See when other users are typing.
- **Read Receipts**: See when your messages have been read.

## Setup

### Prerequisites
- Python 3.8+
- Redis (Required for Channel Layer)

### Installation

1. **Install Dependencies**:
   ```bash
   pip install django channels daphne channels_redis
   ```

2. **Start Redis**:
   Ensure Redis is running on port 6379.
   ```bash
   # If using Docker
   docker run -p 6379:6379 -d redis:5
   ```

3. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

4. **Run Server**:
   ```bash
   python manage.py runserver
   ```

5. **Access**:
   Open [http://localhost:8000](http://localhost:8000) in your browser.

## Project Structure
- `chat/`: Main app containing models, views, consumers, and templates.
- `chat_app/`: Project configuration (ASGI, settings).
- `templates/`: Base templates.

## Usage
1. Enter a username on the login page.
2. In the Lobby, verify "Public Rooms" or create a new one by typing a name and clicking "Join Room".
3. To chat privately, click on a user's name in the "Online Users" list.
4. Watch for "User is typing..." indicators and "Read" status on messages.
