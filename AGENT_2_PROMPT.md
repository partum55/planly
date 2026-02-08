# Agent 2 Prompt: Frontend Clients (Telegram Bot + Desktop App)

## Project Overview

You are building **Planly** - a multi-platform AI agent system for a hackathon. The system has:
1. **Centralized Webserver** - (Other agent) Python FastAPI backend with core AI agent
2. **Telegram Bot Client (YOUR RESPONSIBILITY)** - Forwards messages to webserver
3. **Desktop Electron App (YOUR RESPONSIBILITY)** - Takes screenshots, sends to webserver

Your job is to build the **user-facing interfaces** that interact with the intelligent backend.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  YOUR CLIENTS                                                 │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Telegram Bot Client (Python)                           │ │
│  │  • Listen to group messages                             │ │
│  │  • Forward to webserver: POST /telegram/webhook         │ │
│  │  • Send webserver responses back to Telegram            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Desktop App (Electron - JavaScript/TypeScript)         │ │
│  │  • Global keybind (Cmd+Shift+P)                         │ │
│  │  • Screenshot capture + Tesseract OCR                   │ │
│  │  • POST /agent/process → get proposed actions           │ │
│  │  • Show overlay UI (ChatGPT-style)                      │ │
│  │  • User confirms actions                                │ │
│  │  • POST /agent/confirm-actions → execute                │ │
│  └─────────────────────────────────────────────────────────┘ │
└────────────────────┬──────────────────────────────────────────┘
                     │ HTTP/JSON
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  Webserver (Other Agent Builds This)                         │
│  http://localhost:8000                                        │
│                                                               │
│  Endpoints you will use:                                      │
│  • POST /auth/register, /login, /refresh                     │
│  • POST /agent/process                                        │
│  • POST /agent/confirm-actions                               │
│  • POST /telegram/webhook                                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Part 1: Telegram Bot Client

### Overview
Lightweight Python script that:
1. Listens to all messages in Telegram groups
2. Forwards every message to webserver
3. When webserver returns a response, sends it back to Telegram

### Project Structure
```
telegram-bot/
├── .env.example
├── requirements.txt
├── bot.py           # Main bot script
└── README.md
```

### Implementation

**File:** `telegram-bot/bot.py`

```python
import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBSERVER_URL = os.getenv('WEBSERVER_URL', 'http://localhost:8000')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward all group messages to webserver"""
    message = update.message

    # Skip if no text
    if not message.text:
        return

    # Prepare payload for webserver
    payload = {
        'group_id': message.chat_id,
        'group_title': message.chat.title,
        'message_id': message.message_id,
        'user_id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'text': message.text,
        'timestamp': message.date.isoformat(),
        'is_bot_mention': f'@{context.bot.username}' in message.text
    }

    # Send to webserver
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f'{WEBSERVER_URL}/telegram/webhook',
                json=payload,
                timeout=30.0
            )

            # If webserver returns a response, send it to Telegram
            if response.status_code == 200:
                data = response.json()
                if data.get('response_text'):
                    await message.reply_text(data['response_text'])

        except Exception as e:
            print(f"Error forwarding to webserver: {e}")
            # Don't reply with error to avoid spamming the chat

def main():
    """Start the bot"""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handle all text messages in groups
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS,
        handle_message
    ))

    print("🤖 Telegram bot client started!")
    print(f"📡 Forwarding messages to: {WEBSERVER_URL}")
    print("✅ Add bot to a group and start chatting...")

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

**File:** `telegram-bot/.env.example`

```bash
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
WEBSERVER_URL=http://localhost:8000
```

**File:** `telegram-bot/requirements.txt`

```txt
python-telegram-bot==20.7
httpx==0.26.0
python-dotenv==1.0.0
```

### Setup Instructions

1. **Create Telegram Bot:**
   ```
   1. Open Telegram, search for @BotFather
   2. Send: /newbot
   3. Follow instructions to create bot
   4. Copy bot token
   5. IMPORTANT: Send /setprivacy to @BotFather → Select your bot → Disable
      (This allows bot to read all messages in groups)
   ```

2. **Install dependencies:**
   ```bash
   cd telegram-bot
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token
   ```

4. **Run:**
   ```bash
   python bot.py
   ```

5. **Test:**
   - Add bot to a test Telegram group
   - Send messages in the group
   - Verify bot forwards messages to webserver (check webserver logs)
   - Mention bot: "@your_bot_name book dinner"
   - Bot should reply with response from webserver

---

## Part 2: Desktop Electron App

### Overview
Cross-platform desktop app that:
1. Registers global keybind (Cmd+Shift+P or customizable)
2. Captures screenshot of active window when keybind pressed
3. Runs Tesseract OCR to extract text
4. Sends extracted conversation to webserver
5. Shows beautiful overlay with agent's proposed actions
6. User confirms actions
7. Executes confirmed actions and shows results

### Project Structure
```
desktop-app/
├── package.json
├── main.js                     # Electron main process
├── preload.js                  # Electron preload
├── .env.example
│
├── src/
│   ├── login.html              # Login page
│   ├── overlay.html            # Main overlay UI
│   │
│   ├── renderer/
│   │   ├── login.js            # Login logic
│   │   └── overlay.js          # Overlay logic
│   │
│   ├── services/
│   │   ├── screenshot.js       # Screenshot capture
│   │   ├── ocr.js              # Tesseract OCR
│   │   ├── api-client.js       # HTTP client
│   │   └── auth.js             # Token management
│   │
│   └── styles/
│       ├── main.css            # Global styles
│       └── overlay.css         # Overlay styles
│
└── build/
    └── icon.png                # App icon
```

### Implementation

**File:** `desktop-app/package.json`

```json
{
  "name": "planly-desktop",
  "version": "1.0.0",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder"
  },
  "dependencies": {
    "axios": "^1.6.0",
    "dotenv": "^16.3.1",
    "electron-store": "^8.1.0",
    "screenshot-desktop": "^1.12.7",
    "active-win": "^8.0.0",
    "tesseract.js": "^5.0.3"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.9.1"
  }
}
```

**File:** `desktop-app/main.js`

```javascript
const { app, BrowserWindow, globalShortcut, ipcMain } = require('electron');
const path = require('path');
const screenshot = require('screenshot-desktop');
const activeWindow = require('active-win');
require('dotenv').config();

let overlayWindow;
let loginWindow;
let isAuthenticated = false;

// Create overlay window (hidden by default)
function createOverlayWindow() {
    overlayWindow = new BrowserWindow({
        width: 600,
        height: 800,
        show: false,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    overlayWindow.loadFile('src/overlay.html');
}

// Create login window
function createLoginWindow() {
    loginWindow = new BrowserWindow({
        width: 400,
        height: 500,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    loginWindow.loadFile('src/login.html');
}

app.whenReady().then(() => {
    // Check if user is authenticated
    // If not, show login window
    // If yes, register keybind

    createLoginWindow(); // For now, always show login

    // Register global keybind
    const ret = globalShortcut.register('CommandOrControl+Shift+P', async () => {
        if (!isAuthenticated) {
            console.log('Not authenticated');
            return;
        }

        console.log('🔥 Keybind pressed! Capturing screenshot...');

        try {
            // Get active window info
            const activeWin = await activeWindow();

            // Capture screenshot
            const imgBuffer = await screenshot();

            // Show overlay with loading state
            overlayWindow.show();
            overlayWindow.webContents.send('show-loading');

            // Send to renderer for OCR processing
            overlayWindow.webContents.send('process-screenshot', {
                image: imgBuffer.toString('base64'),
                windowTitle: activeWin.title,
                appName: activeWin.owner.name
            });

        } catch (error) {
            console.error('Error capturing screenshot:', error);
        }
    });

    if (!ret) {
        console.log('Failed to register keybind');
    }

    createOverlayWindow();
});

// Handle login success
ipcMain.on('login-success', (event, tokens) => {
    isAuthenticated = true;
    loginWindow.close();
    console.log('✅ Login successful! Press Cmd+Shift+P to capture.');
});

// Handle close overlay
ipcMain.on('close-overlay', () => {
    overlayWindow.hide();
});

app.on('will-quit', () => {
    globalShortcut.unregisterAll();
});
```

**File:** `desktop-app/src/services/ocr.js`

```javascript
const Tesseract = require('tesseract.js');

async function extractTextFromImage(imageBuffer) {
    console.log('🔍 Running OCR...');

    const { data: { text, confidence } } = await Tesseract.recognize(
        imageBuffer,
        'eng',
        {
            logger: (m) => {
                if (m.status === 'recognizing text') {
                    console.log(`OCR Progress: ${Math.round(m.progress * 100)}%`);
                }
            }
        }
    );

    console.log(`✅ OCR Complete! Confidence: ${confidence.toFixed(2)}%`);

    // Parse text into messages (simple heuristic)
    const messages = parseMessagesFromText(text);

    return { text, confidence, messages };
}

function parseMessagesFromText(text) {
    /**
     * Try to extract messages from OCR text
     * This is a simple heuristic - adjust based on actual chat app formats
     *
     * Example formats:
     * Discord: "Username\n10:30 PM\nMessage text"
     * WhatsApp: "Username, 10:30 PM: Message text"
     */

    const lines = text.split('\n').filter(line => line.trim());
    const messages = [];

    let currentUser = null;
    let currentText = '';

    for (let line of lines) {
        // Try to detect username patterns
        // This is a simple heuristic - you may need to adjust
        if (line.match(/^[A-Z][a-z]+\s*$/)) {
            // Looks like a username
            if (currentUser && currentText) {
                messages.push({
                    username: currentUser,
                    text: currentText.trim(),
                    timestamp: new Date().toISOString()
                });
            }
            currentUser = line.trim();
            currentText = '';
        } else if (line.match(/^\d{1,2}:\d{2}\s*(AM|PM)?/)) {
            // Looks like a timestamp - skip
            continue;
        } else {
            // Message text
            currentText += ' ' + line;
        }
    }

    // Add last message
    if (currentUser && currentText) {
        messages.push({
            username: currentUser,
            text: currentText.trim(),
            timestamp: new Date().toISOString()
        });
    }

    return messages;
}

module.exports = { extractTextFromImage };
```

**File:** `desktop-app/src/services/api-client.js`

```javascript
const axios = require('axios');
const Store = require('electron-store');

const store = new Store();
const WEBSERVER_URL = process.env.WEBSERVER_URL || 'http://localhost:8000';

class APIClient {
    constructor() {
        this.baseURL = WEBSERVER_URL;
        this.accessToken = store.get('access_token');
    }

    async login(email, password) {
        const response = await axios.post(`${this.baseURL}/auth/login`, {
            email,
            password
        });

        const { access_token, refresh_token } = response.data;
        store.set('access_token', access_token);
        store.set('refresh_token', refresh_token);
        this.accessToken = access_token;

        return response.data;
    }

    async processConversation(messages, metadata) {
        const response = await axios.post(
            `${this.baseURL}/agent/process`,
            {
                source: 'desktop_screenshot',
                context: {
                    messages,
                    screenshot_metadata: metadata
                }
            },
            {
                headers: {
                    'Authorization': `Bearer ${this.accessToken}`
                }
            }
        );

        return response.data;
    }

    async confirmActions(conversationId, actionIds) {
        const response = await axios.post(
            `${this.baseURL}/agent/confirm-actions`,
            {
                conversation_id: conversationId,
                action_ids: actionIds
            },
            {
                headers: {
                    'Authorization': `Bearer ${this.accessToken}`
                }
            }
        );

        return response.data;
    }
}

module.exports = APIClient;
```

**File:** `desktop-app/src/overlay.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Planly Agent</title>
    <link rel="stylesheet" href="styles/overlay.css">
</head>
<body>
    <div class="overlay-container">
        <!-- Header -->
        <div class="overlay-header">
            <h2>🤖 Planly Agent</h2>
            <button id="close-btn" class="close-btn">✕</button>
        </div>

        <!-- Loading State -->
        <div id="loading-state" class="loading-state">
            <div class="spinner"></div>
            <p>Analyzing conversation...</p>
        </div>

        <!-- Content -->
        <div id="content-state" style="display: none;">
            <!-- Extracted Conversation -->
            <div class="section">
                <h3>📝 Detected Conversation</h3>
                <div id="messages-list" class="messages-list"></div>
            </div>

            <!-- Understood Intent -->
            <div class="section">
                <h3>🎯 Understood Intent</h3>
                <div class="intent-display">
                    <p><strong>Activity:</strong> <span id="activity-type"></span></p>
                    <p><strong>Participants:</strong> <span id="participants"></span></p>
                    <p><strong>Time:</strong> <span id="event-time"></span></p>
                    <p><strong>Location:</strong> <span id="location"></span></p>
                </div>
            </div>

            <!-- Proposed Actions -->
            <div class="section">
                <h3>⚡ Proposed Actions</h3>
                <div id="actions-list" class="actions-list"></div>
            </div>

            <!-- Buttons -->
            <div class="overlay-footer">
                <button id="cancel-btn" class="btn btn-secondary">Cancel</button>
                <button id="confirm-btn" class="btn btn-primary">Confirm & Execute</button>
            </div>
        </div>

        <!-- Results -->
        <div id="results-state" style="display: none;">
            <div class="section">
                <h3>✅ Actions Completed</h3>
                <div id="results-list"></div>
            </div>
            <button id="done-btn" class="btn btn-primary">Done</button>
        </div>
    </div>

    <script>
        const { ipcRenderer } = require('electron');
        const { extractTextFromImage } = require('./services/ocr');
        const APIClient = require('./services/api-client');

        const apiClient = new APIClient();

        let currentConversationId = null;
        let currentActions = [];

        // Listen for screenshot processing
        ipcRenderer.on('process-screenshot', async (event, data) => {
            const { image, windowTitle, appName } = data;

            try {
                // Run OCR
                const imageBuffer = Buffer.from(image, 'base64');
                const { text, confidence, messages } = await extractTextFromImage(imageBuffer);

                console.log('Extracted messages:', messages);

                // Send to webserver
                const response = await apiClient.processConversation(messages, {
                    window_title: windowTitle,
                    app_name: appName,
                    ocr_confidence: confidence
                });

                // Display results
                displayConversation(messages);
                displayIntent(response.intent);
                displayActions(response.proposed_actions);

                currentConversationId = response.conversation_id;
                currentActions = response.proposed_actions;

                // Hide loading, show content
                document.getElementById('loading-state').style.display = 'none';
                document.getElementById('content-state').style.display = 'block';

            } catch (error) {
                console.error('Error processing screenshot:', error);
                alert('Error processing screenshot. Please try again.');
                ipcRenderer.send('close-overlay');
            }
        });

        function displayConversation(messages) {
            const list = document.getElementById('messages-list');
            list.innerHTML = messages.map(msg => `
                <div class="message">
                    <strong>${msg.username}:</strong> ${msg.text}
                </div>
            `).join('');
        }

        function displayIntent(intent) {
            document.getElementById('activity-type').textContent = intent.activity_type;
            document.getElementById('participants').textContent = intent.participants.join(', ');
            document.getElementById('event-time').textContent = intent.datetime || 'Not specified';
            document.getElementById('location').textContent = intent.location || 'Not specified';
        }

        function displayActions(actions) {
            const list = document.getElementById('actions-list');
            list.innerHTML = actions.map(action => `
                <label class="action-item">
                    <input type="checkbox" checked data-action-id="${action.action_id}">
                    <div>
                        <strong>${action.tool}</strong>
                        <p>${action.description}</p>
                    </div>
                </label>
            `).join('');
        }

        // Confirm button
        document.getElementById('confirm-btn').addEventListener('click', async () => {
            // Get selected action IDs
            const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
            const actionIds = Array.from(checkboxes).map(cb => cb.dataset.actionId);

            if (actionIds.length === 0) {
                alert('Please select at least one action');
                return;
            }

            // Show loading
            document.getElementById('content-state').style.display = 'none';
            document.getElementById('loading-state').style.display = 'block';
            document.querySelector('.loading-state p').textContent = 'Executing actions...';

            try {
                // Execute actions
                const results = await apiClient.confirmActions(currentConversationId, actionIds);

                // Show results
                displayResults(results.results);
                document.getElementById('loading-state').style.display = 'none';
                document.getElementById('results-state').style.display = 'block';

            } catch (error) {
                console.error('Error executing actions:', error);
                alert('Error executing actions. Please try again.');
            }
        });

        function displayResults(results) {
            const list = document.getElementById('results-list');
            list.innerHTML = results.map(result => `
                <div class="result-item ${result.success ? 'success' : 'error'}">
                    ${result.success ? '✅' : '❌'} ${result.tool}
                    ${result.result?.event_link ? `<a href="${result.result.event_link}" target="_blank">View Event</a>` : ''}
                </div>
            `).join('');
        }

        // Close buttons
        document.getElementById('close-btn').addEventListener('click', () => {
            ipcRenderer.send('close-overlay');
        });

        document.getElementById('cancel-btn').addEventListener('click', () => {
            ipcRenderer.send('close-overlay');
        });

        document.getElementById('done-btn').addEventListener('click', () => {
            ipcRenderer.send('close-overlay');
        });
    </script>
</body>
</html>
```

**File:** `desktop-app/src/styles/overlay.css`

```css
/* ChatGPT-inspired dark theme */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    background: transparent;
}

.overlay-container {
    width: 600px;
    max-height: 90vh;
    background: #1e1e1e;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    color: #e0e0e0;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.overlay-header {
    background: #2a2a2a;
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #3a3a3a;
}

.overlay-header h2 {
    font-size: 18px;
    font-weight: 600;
}

.close-btn {
    background: transparent;
    border: none;
    color: #e0e0e0;
    font-size: 24px;
    cursor: pointer;
    padding: 0;
    width: 30px;
    height: 30px;
}

.close-btn:hover {
    color: #ff4444;
}

.loading-state {
    padding: 60px 20px;
    text-align: center;
}

.spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #3a3a3a;
    border-top-color: #10a37f;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 20px;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

#content-state {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
}

.section {
    margin-bottom: 24px;
}

.section h3 {
    font-size: 16px;
    margin-bottom: 12px;
    color: #10a37f;
}

.messages-list {
    background: #2a2a2a;
    border-radius: 8px;
    padding: 12px;
    max-height: 150px;
    overflow-y: auto;
}

.message {
    margin-bottom: 8px;
    font-size: 14px;
}

.intent-display p {
    margin-bottom: 8px;
    font-size: 14px;
}

.actions-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.action-item {
    display: flex;
    gap: 12px;
    padding: 12px;
    background: #2a2a2a;
    border-radius: 8px;
    cursor: pointer;
}

.action-item:hover {
    background: #323232;
}

.action-item input[type="checkbox"] {
    width: 20px;
    height: 20px;
    cursor: pointer;
}

.overlay-footer {
    padding: 16px 20px;
    border-top: 1px solid #3a3a3a;
    display: flex;
    gap: 12px;
    justify-content: flex-end;
}

.btn {
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-primary {
    background: #10a37f;
    color: white;
}

.btn-primary:hover {
    background: #0e8c6f;
}

.btn-secondary {
    background: #3a3a3a;
    color: #e0e0e0;
}

.btn-secondary:hover {
    background: #4a4a4a;
}

#results-state {
    padding: 20px;
}

.result-item {
    padding: 12px;
    margin-bottom: 8px;
    border-radius: 6px;
    font-size: 14px;
}

.result-item.success {
    background: #1a4d2e;
}

.result-item.error {
    background: #4d1a1a;
}

.result-item a {
    color: #10a37f;
    text-decoration: none;
    margin-left: 8px;
}
```

### Setup Instructions

1. **Install Node.js** (if not already installed)

2. **Install dependencies:**
   ```bash
   cd desktop-app
   npm install
   ```

3. **Configure:**
   ```bash
   # Create .env file
   echo "WEBSERVER_URL=http://localhost:8000" > .env
   ```

4. **Run in development:**
   ```bash
   npm start
   ```

5. **Test:**
   - Login with credentials (register via webserver first)
   - Open any chat app (Discord, WhatsApp, etc.)
   - Have a conversation
   - Press Cmd+Shift+P (or Ctrl+Shift+P on Windows)
   - Overlay should appear with extracted conversation
   - Confirm actions
   - Check that calendar event is created

---

## API Contract (What You Need from Other Agent)

### Endpoints You Will Use

#### 1. POST /auth/login
```
Request:
{
    "email": "test@example.com",
    "password": "testpass"
}

Response:
{
    "user_id": "uuid",
    "access_token": "jwt_token",
    "refresh_token": "refresh_token"
}
```

#### 2. POST /agent/process
```
Request:
Headers: Authorization: Bearer <access_token>
{
    "source": "desktop_screenshot",
    "context": {
        "messages": [
            {"username": "Alice", "text": "...", "timestamp": "..."}
        ],
        "screenshot_metadata": {
            "window_title": "Discord",
            "app_name": "Discord",
            "ocr_confidence": 0.95
        }
    }
}

Response:
{
    "conversation_id": "uuid",
    "intent": {
        "activity_type": "restaurant",
        "participants": ["Alice", "Bob"],
        "datetime": "2026-02-09T19:00:00Z",
        "location": "Downtown"
    },
    "proposed_actions": [
        {
            "action_id": "uuid",
            "tool": "restaurant_search",
            "description": "Search for restaurants in Downtown",
            "parameters": {...}
        },
        {
            "action_id": "uuid",
            "tool": "calendar_create_event",
            "description": "Create calendar event for dinner",
            "parameters": {...}
        }
    ]
}
```

#### 3. POST /agent/confirm-actions
```
Request:
Headers: Authorization: Bearer <access_token>
{
    "conversation_id": "uuid",
    "action_ids": ["uuid1", "uuid2"]
}

Response:
{
    "results": [
        {
            "action_id": "uuid1",
            "tool": "restaurant_search",
            "success": true,
            "result": {
                "restaurants": [...]
            }
        },
        {
            "action_id": "uuid2",
            "tool": "calendar_create_event",
            "success": true,
            "result": {
                "event_id": "google_cal_id",
                "event_link": "https://calendar.google.com/..."
            }
        }
    ]
}
```

#### 4. POST /telegram/webhook
```
Request:
{
    "group_id": 123456,
    "message_id": 789,
    "user_id": 111,
    "username": "alice",
    "text": "Let's get dinner tomorrow",
    "timestamp": "2026-02-08T18:00:00Z",
    "is_bot_mention": false
}

Response:
{
    "response_text": "..." | null
}
```

---

## Success Criteria

✅ Telegram bot forwards all messages to webserver
✅ Telegram bot sends webserver responses back to group
✅ Desktop app captures screenshots on keybind
✅ Desktop app extracts text via Tesseract OCR
✅ Desktop app shows overlay with agent proposals
✅ Desktop app can confirm actions and show results
✅ Beautiful ChatGPT-style UI
✅ Works with Discord, WhatsApp, Slack, etc.

---

## Testing Strategy

### Telegram Bot Testing
1. Start webserver (other agent)
2. Start telegram bot: `python bot.py`
3. In Telegram group:
   - Send normal messages → verify forwarded to webserver
   - Mention bot → verify response comes back
4. Check webserver logs to see incoming requests

### Desktop App Testing
1. Start webserver (other agent)
2. Start desktop app: `npm start`
3. Login with test credentials
4. Open Discord/WhatsApp
5. Have a fake conversation:
   ```
   You: "Let's grab lunch tomorrow at noon"
   (Switch users/windows to simulate friend)
   Friend: "Sure, I'm in!"
   ```
6. Press keybind (Cmd+Shift+P)
7. Verify:
   - Screenshot captured
   - OCR extracts text
   - Overlay shows with detected conversation
   - Can confirm actions
   - Calendar event created

---

## Tips

1. **Telegram Bot:** Keep it simple - just forward and reply
2. **Desktop App:** Start with basic screenshot + OCR, then add UI polish
3. **OCR Parsing:** Different chat apps have different formats - you may need to adjust the parsing logic
4. **Error Handling:** Always handle network errors gracefully
5. **Mock Mode:** You can mock the webserver responses initially to develop UI faster

---

## Your Next Steps

1. **Telegram Bot:**
   - Create project structure
   - Implement bot.py
   - Get bot token from @BotFather
   - Test message forwarding

2. **Desktop App:**
   - Set up Electron project
   - Implement keybind and screenshot capture
   - Integrate Tesseract OCR
   - Build overlay UI
   - Integrate API client
   - Test end-to-end

3. **Integration:**
   - Coordinate with other agent on API contract
   - Test both clients with webserver
   - Verify end-to-end flows work

Good luck! 🚀
