Django Chat App - Technical FAQ & Troubleshooting Guide
========================================================

TABLE OF CONTENTS
-----------------
1. Message Delivery & Retry Logic
2. WebSocket Connection Management
3. Payload Structure & Debugging
4. Minimum Required Model Fields
5. Performance & Scalability
6. Common Issues & Solutions

========================================================
1. MESSAGE DELIVERY & RETRY LOGIC
========================================================

1.1. How to Retry Message Sending if Not Delivered?
----------------------------------------------------

CURRENT IMPLEMENTATION:
- Messages are saved to the database immediately when sent
- If WebSocket fails, the message is still in DB but not delivered in real-time
- When user reconnects, they see all messages from DB (historical load)

RECOMMENDED RETRY IMPLEMENTATION:

A) Client-Side Retry (Recommended for this app):

```javascript
// In chatPage.html, add this retry logic:

let messageQueue = [];
let isConnected = false;

chatSocket.onopen = function(e) {
    console.log('WebSocket connected');
    isConnected = true;
    
    // Send any queued messages
    while (messageQueue.length > 0) {
        const msg = messageQueue.shift();
        chatSocket.send(JSON.stringify(msg));
    }
};

chatSocket.onerror = function(e) {
    console.error('WebSocket error:', e);
    isConnected = false;
};

chatSocket.onclose = function(e) {
    console.log('WebSocket closed');
    isConnected = false;
    
    // Attempt to reconnect after 3 seconds
    setTimeout(() => {
        console.log('Attempting to reconnect...');
        location.reload(); // Simple reconnect
    }, 3000);
};

// Modified send function with retry
function sendMessage(message) {
    const payload = {
        'type': 'chat_message',
        'message': message,
        'username': username
    };
    
    if (isConnected) {
        chatSocket.send(JSON.stringify(payload));
    } else {
        // Queue message for retry
        messageQueue.push(payload);
        console.log('Message queued for retry');
        
        // Show user feedback
        alert('Connection lost. Message will be sent when reconnected.');
    }
}
```

B) Server-Side Acknowledgment Pattern:

```javascript
// Client sends with unique ID
const msgId = Date.now() + '_' + Math.random();
chatSocket.send(JSON.stringify({
    'type': 'chat_message',
    'message': 'Hello',
    'username': 'alice',
    'client_msg_id': msgId
}));

// Wait for server ACK
const pendingMessages = new Map();
pendingMessages.set(msgId, { message: 'Hello', timestamp: Date.now() });

// Server should respond with ACK
chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    
    if (data.type === 'ack') {
        pendingMessages.delete(data.client_msg_id);
    }
};

// Retry after 5 seconds if no ACK
setInterval(() => {
    const now = Date.now();
    pendingMessages.forEach((msg, id) => {
        if (now - msg.timestamp > 5000) {
            // Retry
            chatSocket.send(JSON.stringify({
                'type': 'chat_message',
                'message': msg.message,
                'username': username,
                'client_msg_id': id
            }));
        }
    });
}, 5000);
```

1.2. Message Notifications
---------------------------

CURRENT IMPLEMENTATION:
- Real-time notifications via WebSocket to lobby
- Green badge shows unread count
- Browser tab title can be updated

ENHANCED NOTIFICATION OPTIONS:

A) Browser Notifications (Desktop):

```javascript
// Request permission on page load
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

// In handleChatMessage function, add:
function handleChatMessage(data) {
    // ... existing code ...
    
    // If message is not from me and window is not focused
    if (!isMe && !document.hasFocus()) {
        if (Notification.permission === 'granted') {
            new Notification(`New message from ${data.username}`, {
                body: data.message,
                icon: '/static/chat-icon.png',
                tag: 'chat-notification'
            });
        }
    }
}
```

B) Audio Notification:

```javascript
const notificationSound = new Audio('/static/notification.mp3');

function handleChatMessage(data) {
    if (!isMe) {
        notificationSound.play().catch(e => console.log('Audio play failed:', e));
    }
}
```

C) Tab Title Notification:

```javascript
let originalTitle = document.title;
let unreadCount = 0;

function handleChatMessage(data) {
    if (!isMe && !document.hasFocus()) {
        unreadCount++;
        document.title = `(${unreadCount}) ${originalTitle}`;
    }
}

window.addEventListener('focus', () => {
    unreadCount = 0;
    document.title = originalTitle;
});
```

========================================================
2. WEBSOCKET CONNECTION MANAGEMENT
========================================================

2.1. How Many WebSocket Connections Can Be Kept Live?
------------------------------------------------------

THEORETICAL LIMITS:
- Browser: ~200-256 connections per browser (across all tabs)
- Server (Daphne): Depends on system resources
  * Each connection uses ~1-2 MB of RAM
  * 1000 connections ≈ 1-2 GB RAM
  * 10,000 connections ≈ 10-20 GB RAM

PRACTICAL LIMITS FOR THIS APP:

A) Single Server Setup (Current):
   - Recommended: 500-1000 concurrent connections
   - Maximum: 2000-5000 (with 8GB RAM, optimized settings)

B) Redis Channel Layer:
   - Supports horizontal scaling
   - Can handle 10,000+ connections across multiple servers

C) Per User:
   - Current app: 1 connection per chat room + 1 for lobby
   - If user has 5 tabs open: 5-10 connections
   - Recommended: Implement connection pooling/sharing

MONITORING CONNECTION COUNT:

```python
# Add to consumers.py
import logging
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    active_connections = 0
    
    async def connect(self):
        ChatConsumer.active_connections += 1
        logger.info(f"Active connections: {ChatConsumer.active_connections}")
        # ... rest of connect logic
    
    async def disconnect(self, close_code):
        ChatConsumer.active_connections -= 1
        logger.info(f"Active connections: {ChatConsumer.active_connections}")
        # ... rest of disconnect logic
```

2.2. What to Do If Connection Is Lost?
---------------------------------------

AUTOMATIC RECONNECTION STRATEGY:

```javascript
// Add to chatPage.html

let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000; // 3 seconds

function connectWebSocket() {
    const wsUrl = 'ws://' + window.location.host + '/ws/chat/group/' + roomName + '/';
    const chatSocket = new WebSocket(wsUrl);
    
    chatSocket.onopen = function(e) {
        console.log('WebSocket connected');
        reconnectAttempts = 0;
        
        // Update UI to show connected status
        document.getElementById('connection-status').textContent = 'Connected';
        document.getElementById('connection-status').style.color = 'green';
    };
    
    chatSocket.onclose = function(e) {
        console.log('WebSocket closed:', e.code, e.reason);
        
        // Update UI to show disconnected status
        document.getElementById('connection-status').textContent = 'Disconnected';
        document.getElementById('connection-status').style.color = 'red';
        
        // Attempt to reconnect
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            console.log(`Reconnecting... Attempt ${reconnectAttempts}`);
            
            setTimeout(() => {
                connectWebSocket();
            }, RECONNECT_DELAY * reconnectAttempts); // Exponential backoff
        } else {
            console.error('Max reconnection attempts reached');
            alert('Connection lost. Please refresh the page.');
        }
    };
    
    chatSocket.onerror = function(e) {
        console.error('WebSocket error:', e);
    };
    
    return chatSocket;
}

// Initialize connection
let chatSocket = connectWebSocket();
```

ADD CONNECTION STATUS INDICATOR TO HTML:

```html
<!-- Add to chatPage.html header -->
<div style="position: fixed; top: 10px; right: 10px; padding: 5px 10px; 
            background: white; border-radius: 5px; font-size: 0.8rem;">
    Status: <span id="connection-status" style="color: green;">Connected</span>
</div>
```

========================================================
3. PAYLOAD STRUCTURE & DEBUGGING
========================================================

3.1. WebSocket Payload Structure
---------------------------------

ALL MESSAGE TYPES SENT IN THIS APP:

A) CHAT MESSAGE (Client → Server):
```json
{
    "type": "chat_message",
    "message": "Hello, world!",
    "username": "alice"
}
```

B) CHAT MESSAGE (Server → Client):
```json
{
    "type": "chat_message",
    "message": "Hello, world!",
    "username": "alice",
    "id": 123
}
```

C) TYPING INDICATOR (Client → Server):
```json
{
    "type": "typing",
    "is_typing": true,
    "username": "alice"
}
```

D) TYPING INDICATOR (Server → Client):
```json
{
    "type": "typing",
    "username": "alice",
    "is_typing": true
}
```

E) READ RECEIPT (Client → Server):
```json
{
    "type": "read_receipt",
    "message_id": 123,
    "username": "bob"
}
```

F) READ RECEIPT (Server → Client):
```json
{
    "type": "read_receipt",
    "message_id": 123,
    "username": "bob"
}
```

G) BULK READ (Server → Client):
```json
{
    "type": "bulk_read",
    "message_ids": [101, 102, 103],
    "username": "bob"
}
```

H) NOTIFICATION (Server → Client - Lobby):
```json
{
    "type": "notification",
    "sender": "alice",
    "target_user": "bob",
    "room_type": "private"
}
```
OR
```json
{
    "type": "notification",
    "sender": "alice",
    "room_name": "general",
    "room_type": "group"
}
```

3.2. How to Debug WebSocket Connection
---------------------------------------

METHOD 1: Browser Developer Tools

1. Open Chrome DevTools (F12)
2. Go to "Network" tab
3. Filter by "WS" (WebSocket)
4. Click on the WebSocket connection
5. View "Messages" tab to see all sent/received data

METHOD 2: Add Debug Console to HTML Page

```html
<!-- Add to chatPage.html -->
<div id="debug-console" style="position: fixed; bottom: 0; left: 0; right: 0; 
     height: 200px; background: #000; color: #0f0; overflow-y: auto; 
     font-family: monospace; font-size: 12px; padding: 10px; display: none;">
    <button onclick="document.getElementById('debug-console').style.display='none'"
            style="position: absolute; top: 5px; right: 5px;">Close</button>
    <div id="debug-log"></div>
</div>
<button onclick="document.getElementById('debug-console').style.display='block'"
        style="position: fixed; bottom: 10px; right: 10px; z-index: 9999;">
    Debug
</button>

<script>
function debugLog(message, data) {
    const log = document.getElementById('debug-log');
    const timestamp = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.innerHTML = `[${timestamp}] ${message}: ${JSON.stringify(data, null, 2)}`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

// Wrap WebSocket methods
const originalSend = chatSocket.send;
chatSocket.send = function(data) {
    debugLog('SENT', JSON.parse(data));
    return originalSend.call(this, data);
};

chatSocket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    debugLog('RECEIVED', data);
    
    // ... rest of your onmessage handler
};
</script>
```

METHOD 3: Check Connection Status Programmatically

```javascript
// Add this function to check WebSocket status
function checkWebSocketStatus() {
    const states = {
        0: 'CONNECTING',
        1: 'OPEN',
        2: 'CLOSING',
        3: 'CLOSED'
    };
    
    console.log('WebSocket State:', states[chatSocket.readyState]);
    console.log('WebSocket URL:', chatSocket.url);
    console.log('WebSocket Protocol:', chatSocket.protocol);
    
    return chatSocket.readyState === 1; // Returns true if OPEN
}

// Call from browser console:
// checkWebSocketStatus()
```

METHOD 4: Server-Side Logging

```python
# In consumers.py, add detailed logging:

import logging
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info(f"WebSocket CONNECT: {self.scope['user']} to {self.room_name}")
        # ... rest of code
    
    async def receive(self, text_data):
        logger.info(f"WebSocket RECEIVE: {text_data}")
        # ... rest of code
    
    async def disconnect(self, close_code):
        logger.info(f"WebSocket DISCONNECT: {self.scope['user']} code={close_code}")
        # ... rest of code
```

========================================================
4. MINIMUM REQUIRED MODEL FIELDS
========================================================

4.1. Absolute Minimum for Basic Chat
-------------------------------------

USER MODEL (Django's built-in):
- id (auto)
- username (required)

CHATROOM MODEL:
```python
class ChatRoom(models.Model):
    name = models.CharField(max_length=255, unique=True)
    # That's it! Minimum required.
```

MESSAGE MODEL:
```python
class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # That's it! Minimum required.
```

4.2. Recommended Fields for Production
---------------------------------------

CHATROOM MODEL:
```python
class ChatRoom(models.Model):
    name = models.CharField(max_length=255, unique=True)  # REQUIRED
    type = models.CharField(max_length=10, choices=[...]) # For private/group
    participants = models.ManyToManyField(User)           # For access control
    created_at = models.DateTimeField(auto_now_add=True)  # For sorting
    is_active = models.BooleanField(default=True)         # For soft delete
```

MESSAGE MODEL:
```python
class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)  # REQUIRED
    sender = models.ForeignKey(User, on_delete=models.CASCADE)    # REQUIRED
    content = models.TextField()                                   # REQUIRED
    timestamp = models.DateTimeField(auto_now_add=True)           # REQUIRED
    
    # Optional but recommended:
    read_by = models.ManyToManyField(User, related_name='read_messages')
    is_deleted = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
```

4.3. What Each Field Enables
-----------------------------

ChatRoom.type:
  ✓ Enables: Private vs Group chat distinction
  ✗ Without it: All chats treated the same

ChatRoom.participants:
  ✓ Enables: Access control, member lists
  ✗ Without it: Anyone can join any room

Message.read_by:
  ✓ Enables: Read receipts, unread counts
  ✗ Without it: No way to track who read what

Message.timestamp:
  ✓ Enables: Message ordering, date grouping
  ✗ Without it: Messages in random order

========================================================
5. PERFORMANCE & SCALABILITY
========================================================

5.1. Current App Capacity
-------------------------

SINGLE SERVER (8GB RAM):
- Concurrent Users: 500-1000
- Messages/Second: 100-500
- Database Size: Unlimited (SQLite handles GB of data)

BOTTLENECKS:
1. Redis Channel Layer (in-memory)
2. Database writes (SQLite is single-threaded)
3. WebSocket connections (RAM usage)

5.2. Scaling Strategies
-----------------------

HORIZONTAL SCALING:
```
Load Balancer
    ├── Django Server 1 (Daphne)
    ├── Django Server 2 (Daphne)
    └── Django Server 3 (Daphne)
            ↓
    Redis (Channel Layer)
            ↓
    PostgreSQL Database
```

VERTICAL SCALING:
- Upgrade to PostgreSQL (handles concurrent writes better)
- Increase Redis memory
- Add more CPU cores for Daphne workers

========================================================
6. COMMON ISSUES & SOLUTIONS
========================================================

ISSUE: "WebSocket connection failed"
SOLUTION: Check if Redis is running: `redis-cli ping`

ISSUE: "Messages not appearing in real-time"
SOLUTION: Check browser console for WebSocket errors

ISSUE: "Unread counts not updating"
SOLUTION: Ensure lobby WebSocket is connected

ISSUE: "Blue ticks appearing for sender"
SOLUTION: Fixed in latest code (checks read_by.count > 1)

ISSUE: "Can't create new rooms"
SOLUTION: Fixed URL routing (removed duplicate /chat/ prefix)

========================================================
END OF TECHNICAL FAQ
========================================================
