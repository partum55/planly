# Planly Backend API Specification

**Base URL:** `http://localhost:8000` (or configure PORT in .env)

**Version:** 1.0
**Updated:** 2026-02-09

This document describes all API endpoints implemented by Agent 1 (Backend Server) for use by Agent 2 (Telegram Bot + Desktop App).

---

## Authentication

All endpoints except the following require `Authorization: Bearer <access_token>` header:
- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/refresh`
- `POST /auth/google/callback`
- `POST /auth/link-telegram`

---

## Endpoints

### 1. POST /auth/register

Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secret",
  "full_name": "John Doe"
}
```

**Response (200):**
```json
{
  "user_id": "uuid-string",
  "access_token": "jwt...",
  "refresh_token": "jwt..."
}
```

**Errors:**
- `400` - Email already exists or invalid input
- `500` - Server error

---

### 2. POST /auth/login

Login with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

**Response (200):**
```json
{
  "user_id": "uuid-string",
  "access_token": "jwt...",
  "refresh_token": "jwt..."
}
```

**Errors:**
- `401` - Invalid credentials
- `500` - Server error

---

### 3. POST /auth/refresh

Refresh access token. Desktop app calls this on startup to validate saved tokens, and automatically on any 401.

**Request:**
```json
{
  "refresh_token": "jwt..."
}
```

**Response (200):**
```json
{
  "access_token": "jwt...",
  "refresh_token": "jwt..."
}
```

**Errors:**
- `401` - Token invalid/expired (desktop should clear saved tokens and show login)
- `500` - Server error

---

### 4. POST /auth/google/callback

Google OAuth callback for desktop app "Continue with Google" button.

**Desktop Flow:**
1. Opens Google OAuth consent window
2. Captures authorization code
3. POSTs code to this endpoint
4. Receives JWT tokens

**Request:**
```json
{
  "code": "4/0AX4XfWh..."
}
```

**Response (200):**
```json
{
  "user_id": "uuid-string",
  "access_token": "jwt...",
  "refresh_token": "jwt..."
}
```

**Backend Implementation:**
1. Exchange `code` with Google at `https://oauth2.googleapis.com/token` using `client_id` + `client_secret` + `redirect_uri=http://localhost:8000/auth/google/callback`
2. Fetch user info from `https://www.googleapis.com/oauth2/v2/userinfo` with the Google access token
3. Find or create user by Google email
4. Return your own JWT tokens (same format as `/auth/login`)

**Google OAuth Configuration:**
- **Scopes:** `openid email profile`
- **Redirect URI:** `http://localhost:8000/auth/google/callback` (desktop intercepts)

**Errors:**
- `400` - Invalid authorization code
- `500` - OAuth authentication failed

---

### 5. GET /auth/me

Validates bearer token and returns user profile. Useful for "Logged in as..." in the UI.

**Request:** Bearer token in `Authorization` header

**Response (200):**
```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "full_name": "John Doe",
  "avatar_url": "https://..."
}
```

**Errors:**
- `401` - Invalid/expired token
- `500` - Server error

---

### 6. POST /auth/link-telegram

Link Telegram account to Planly user account. Used by Telegram bot `/link` command.

**Request:**
```json
{
  "email": "user@example.com",
  "telegram_id": 123456789,
  "telegram_username": "alice"
}
```

**Response (200):**
```json
{
  "success": true,
  "user_id": "uuid-string"
}
```

**Response (404):**
```json
{
  "detail": "No account found with that email"
}
```

**Errors:**
- `404` - Email not found
- `400` - Failed to link account
- `500` - Server error

---

### 7. POST /agent/process

**Main endpoint.** Desktop sends user's typed command + OCR'd screenshot data.

**Request:**
```json
{
  "user_prompt": "appoint dinner tomorrow at 7pm",
  "conversation_id": "uuid-string | null",
  "source": "desktop_screenshot",
  "context": {
    "messages": [
      {
        "username": "Alice",
        "text": "Let's do dinner tomorrow",
        "timestamp": "2:30 PM"
      },
      {
        "username": "Bob",
        "text": "Sure, 7pm works",
        "timestamp": "2:31 PM"
      }
    ],
    "screenshot_metadata": {
      "ocr_confidence": 85.5,
      "raw_text": "full OCR text..."
    }
  }
}
```

**Fields:**
- `user_prompt` (string, required) — what the user typed
- `conversation_id` (string | null) — pass from previous response for multi-turn conversations
- `source` (string) — "desktop_screenshot" or "telegram"
- `context.messages` — OCR-parsed chat messages from the screenshot
- `context.screenshot_metadata.raw_text` — full OCR dump for validation

**Response (200) — returns `blocks[]` array:**
```json
{
  "conversation_id": "uuid-string",
  "blocks": [
    {
      "type": "text",
      "content": "I see a dinner plan. Let me help organize that."
    },
    {
      "type": "action_cards",
      "actions": [
        {
          "action_id": "uuid-string",
          "tool": "calendar_create_event",
          "description": "Create calendar event 'Dinner' on Feb 9 at 7pm",
          "parameters": {
            "title": "Dinner",
            "datetime": "2026-02-09T19:00:00Z",
            "duration_minutes": 120
          }
        }
      ]
    }
  ]
}
```

**Block Types:**

| Type | Fields | When to Use |
|------|--------|-------------|
| `text` | `content: string` | Any text response from the agent |
| `action_cards` | `actions: Action[]` | Proposed actions for user to select/confirm |
| `calendar_picker` | `prompt: string` | Agent needs a date from user |
| `time_picker` | `prompt: string` | Agent needs a time from user |
| `error` | `message: string` | Something went wrong |

**Multi-turn Conversations:**
When `conversation_id` is provided, the backend looks up previous context from database, appends new prompt + messages, and continues the conversation (not start fresh).

This enables flows like:
- User: "appoint dinner" → Agent: "When?" (calendar_picker) → User selects date → Agent returns action_cards

**Screenshot Validation:**
If the screenshot is not useful (no conversation, wrong app), return a `text` block asking for clarification.

**Errors:**
- `401` - Unauthorized
- `404` - Conversation not found (if conversation_id provided)
- `200` with `error` block - Processing error (graceful failure)

---

### 8. POST /agent/confirm-actions

Execute confirmed actions. User selects action cards and hits Confirm. Desktop sends the selected action IDs.

**Request:**
```json
{
  "conversation_id": "uuid-string",
  "action_ids": ["action-uuid-1", "action-uuid-2"]
}
```

**Response (200):**
```json
{
  "success": true,
  "results": [
    {
      "action_id": "action-uuid-1",
      "tool": "calendar_create_event",
      "success": true,
      "result": {
        "event_id": "google_calendar_event_id",
        "event_link": "https://calendar.google.com/..."
      }
    }
  ],
  "formatted_response": "Done! Dinner event created for tomorrow at 7pm."
}
```

**Fields:**
- `success` (boolean) — true if all actions succeeded
- `results` (array) — individual action results
  - `action_id` — matches the ID from /agent/process
  - `tool` — tool that was executed
  - `success` — whether this specific action succeeded
  - `result` — tool-specific result data
  - `error` — error message if failed
- `formatted_response` (string) — human-readable summary

**Errors:**
- `401` - Unauthorized
- `404` - Action plan not found (must call /agent/process first)
- `500` - Execution failed

---

## Summary Table

| # | Endpoint | Method | Auth Required | Purpose |
|---|----------|--------|---------------|---------|
| 1 | `/auth/register` | POST | No | Create new account |
| 2 | `/auth/login` | POST | No | Email/password login |
| 3 | `/auth/refresh` | POST | No | Refresh access token |
| 4 | `/auth/google/callback` | POST | No | Google OAuth login |
| 5 | `/auth/me` | GET | Yes | Get current user profile |
| 6 | `/auth/link-telegram` | POST | No | Link Telegram to account |
| 7 | `/agent/process` | POST | Yes | Process conversation & return actions |
| 8 | `/agent/confirm-actions` | POST | Yes | Execute confirmed actions |

---

## Additional Endpoints (Implemented)

### POST /telegram/webhook

Receive messages from Telegram bot client (used by Telegram bot, not desktop app).

**Request:**
```json
{
  "group_id": 123456,
  "group_title": "Planning Group",
  "message_id": 789,
  "user_id": 111,
  "username": "alice",
  "first_name": "Alice",
  "text": "Let's meet tomorrow",
  "timestamp": "2026-02-09T14:30:00Z",
  "is_bot_mention": false
}
```

**Response (200):**
```json
{
  "response_text": "Bot response text" | null
}
```

---

## Environment Configuration

Required environment variables in `server/.env`:

```bash
# Database
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_service_role_key

# LLM
USE_CLOUD_LLM=true
OLLAMA_ENDPOINT=https://api.groq.com/openai
OLLAMA_MODEL=llama-3.1-8b-instant
LLM_API_KEY=your_api_key

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Google Calendar (optional)
GOOGLE_CALENDAR_ID=calendar_id@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_FILE=./integrations/google_calendar/service_account.json

# JWT
JWT_SECRET_KEY=your_random_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

---

## Interactive API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

These provide interactive API testing and full schema documentation.

---

## Example Desktop App Flow

1. **Startup:**
   - Check for saved refresh_token
   - If exists: `POST /auth/refresh`
   - If 401: Clear tokens, show login screen
   - If 200: Save new tokens, proceed

2. **Login:**
   - User clicks "Login": `POST /auth/login`
   - OR user clicks "Continue with Google": `POST /auth/google/callback`
   - Save tokens to local storage

3. **Process Screenshot:**
   - User takes screenshot + types prompt
   - Desktop OCRs screenshot
   - `POST /agent/process` with user_prompt + OCR'd messages
   - Display blocks returned (text, action cards, etc.)

4. **Confirm Actions:**
   - User selects action cards
   - `POST /agent/confirm-actions` with selected action_ids
   - Display formatted_response to user

5. **Multi-turn:**
   - User provides more info (e.g., picks a date)
   - `POST /agent/process` with same conversation_id
   - Agent continues conversation with full context

---

## Example Telegram Bot Flow

1. **Link Account:**
   - User: `/link user@example.com`
   - Bot: `POST /auth/link-telegram`
   - Bot: "Account linked successfully!"

2. **Receive Messages:**
   - Telegram forwards all group messages: `POST /telegram/webhook`
   - If `is_bot_mention: true`, backend processes and returns response_text
   - Bot sends response_text to group

---

## Testing with curl

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass","full_name":"Test User"}'

# Save the access_token from response

# 2. Process conversation
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "user_prompt": "Schedule dinner tomorrow at 7pm",
    "source": "desktop_screenshot",
    "context": {
      "messages": [
        {"username":"Alice","text":"Lets do dinner tomorrow","timestamp":"2026-02-09T14:00:00Z"},
        {"username":"Bob","text":"7pm works","timestamp":"2026-02-09T14:01:00Z"}
      ]
    }
  }'

# Save conversation_id and action_id from response

# 3. Confirm actions
curl -X POST http://localhost:8000/agent/confirm-actions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "conversation_id": "<conversation_id>",
    "action_ids": ["<action_id>"]
  }'
```

---

## Status

✅ All endpoints implemented and tested
✅ Matches AGENT_1_TASKS.md specification exactly
✅ Ready for Agent 2 integration
✅ Interactive documentation available at /docs

For setup instructions, see: `QUICK_START.md` and `CLOUD_LLM_SETUP.md`
