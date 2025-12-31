# Testing Multiple Users Simultaneously

## The Problem
When testing with multiple users in the same browser (even in incognito mode), Django sessions can conflict because:
- **Incognito tabs in the same window share cookies**
- Django uses cookies to track sessions
- The last login overwrites the session for all tabs

## Solutions for Testing

### Option 1: Use Different Browsers (Recommended)
- User 1 (charlie): Chrome
- User 2 (job): Firefox or Safari
- Each browser has its own session storage

### Option 2: Use Separate Browser Profiles
**Chrome:**
```bash
# Create separate profiles
# Profile 1: chrome://settings/people
# Profile 2: Open new profile window
```

**Firefox:**
```bash
# Use Firefox Multi-Account Containers extension
# Or use different Firefox profiles
```

### Option 3: Use Different Incognito Windows (Not Tabs!)
⚠️ **Important:** Open separate incognito WINDOWS, not tabs
- Window 1: User charlie
- Window 2: User job
- Each window has isolated session storage

### Option 4: Use Browser Developer Tools
```javascript
// In Console, clear cookies for one tab:
document.cookie.split(";").forEach(function(c) { 
    document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
});
```

## How to Test Properly

### Method 1: Two Different Browsers
```
1. Chrome → Login as charlie
2. Firefox → Login as job
3. Open private chat between them
4. Send messages back and forth
5. Leave room - sessions stay separate ✅
```

### Method 2: Chrome Profiles
```
1. Chrome Profile 1 → Login as charlie
2. Chrome Profile 2 → Login as job
3. Test messaging
```

### Method 3: Separate Incognito Windows
```
1. Chrome → New Incognito Window → Login as charlie
2. Chrome → Another New Incognito Window → Login as job
   (Don't use tabs in the same window!)
3. Test messaging
```

## Why This Happens

Django uses `sessionid` cookie to track logged-in users:
```
Cookie: sessionid=abc123...
```

When you have two tabs in the same browser:
1. Tab 1: Login as charlie → Sets sessionid=abc123
2. Tab 2: Login as job → Overwrites sessionid=xyz789
3. Tab 1: Now uses sessionid=xyz789 → Shows as job ❌

## The Fix

I've added these session settings to prevent some conflicts:
```python
SESSION_COOKIE_NAME = 'django_chat_sessionid'
SESSION_SAVE_EVERY_REQUEST = True
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
```

But the **fundamental limitation** is that browsers share cookies across tabs.

## Production Solution

In production, users would:
- Each use their own device/browser
- Have unique sessions
- No conflicts occur

For development testing, use **different browsers** or **separate browser profiles**.
