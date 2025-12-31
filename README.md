# Django Real-Time Chat Application

A high-performance, real-time chat application built with **Django 6.0**, **Django Channels**, and **Redis**. This project serves as a comprehensive "spike" to demonstrate scalable WebSocket architecture, robust notification systems, and premium UI/UX.

## 🚀 Key Features

### 💬 Messaging Experience
- **Real-time Messaging**: Instant delivery powered by WebSockets and Redis.
- **Group & Private Chats**: Support for public rooms and 1-on-1 direct messaging.
- **Premium UI**: WhatsApp-inspired theme with a clean, responsive layout.
- **Message Persistence**: Full chat history saved in SQLite.
- **Message Grouping**: Smart grouping by date (Today, Yesterday, etc.).
- **Typing Indicators**: Real-time "User is typing..." feedback.

### 📊 Status & Read Receipts
- **WhatsApp-style Ticks**:
  - **Sent**: Single Tick (✓)
  - **Read**: Blue Double Tick (✓✓)
- **Bulk Read Sync**: Messages are automatically marked as read when you enter a room or focus the window.

### 🔔 Advanced Notifications
- **Lobby Badges**: Real-time unread count badges for every conversation in the lobby.
- **Desktop Notifications**: Native browser alerts for new messages when the window is out of focus.
- **Tab Title Notifications**: Dynamic unread counts in the browser tab (e.g., `(3) Chat Room`).
- **Manual Permission Control**: Dedicated button to enable/request notification permissions.

### 🛠 Reliability & Performance
- **Robust Reconnection**: Automatic reconnection with exponential backoff and visual status indicators.
- **Connection Monitoring**: Real-time tracking of active socket connections.
- **Redis Error Handling**: Custom middleware to gracefully handle Redis downtime without crashing the app.
- **Session Isolation**: Configured for multi-user testing in the same browser using unique session cookies.

## 🛠 Technology Stack
- **Backend**: Django 6.0, Django Channels 4.0
- **Asynchronous Server**: Daphne (ASGI)
- **Channel Layer**: Redis
- **Database**: SQLite
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3

## 📦 Setup & Installation

### Prerequisites
- Python 3.10+
- Redis Server (Running on port 6379)

### Installation Steps

1. **Clone & Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis**:
   Ensure Redis is running. If using Docker:
   ```bash
   docker run -p 6379:6379 -d redis:5
   ```

3. **Database Setup**:
   ```bash
   python manage.py migrate
   ```

4. **Run the Application**:
   ```bash
   python manage.py runserver
   ```

5. **Access**:
   Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## 📖 Documentation
For in-depth technical details, diagrams, and architectural analysis, please refer to:
- **`implementation_docs.txt`**: Complete technical breakdown in plain text.
- **`Django_Chat_App_Spike_Documentation.docx`**: Executive summary and feature overview.
- **`Django_Chat_App_Technical_Deep_Dive.docx`**: High-fidelity documentation with system diagrams and flowcharts.

## 🧪 Multi-User Testing
To test real-time features between different users:
1. Open the app in two different browsers (e.g., Chrome and Firefox).
2. Or use a standard window and an Incognito/Private window.
3. The app is configured with unique session cookies to prevent login conflicts during local testing.

