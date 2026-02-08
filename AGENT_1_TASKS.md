# Agent 1 Tasks: Full API Spec Required by Agent 2

All endpoints needed by the desktop app and telegram bot. Full request/response schemas below.

**All endpoints except `/auth/login`, `/auth/register`, and `/auth/google/callback` require `Authorization: Bearer <token>` header.**

---

## 1. `POST /auth/login`

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
  "user_id": "uuid",
  "access_token": "jwt...",
  "refresh_token": "jwt..."
}
```

---

## 2. `POST /auth/register`

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
  "user_id": "uuid",
  "access_token": "jwt...",
  "refresh_token": "jwt..."
}
```

---

## 3. `POST /auth/refresh`

Desktop calls this on startup to validate saved tokens, and automatically on any 401.

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

**Response (401):** Token invalid/expired — desktop clears saved tokens and shows login.

---

## 4. `POST /auth/google/callback`

Desktop has a "Continue with Google" button. Opens Google OAuth consent window, captures the authorization code, POSTs it here.

**Request:**
```json
{
  "code": "4/0AX4XfWh..."
}
```

**Response (200):**
```json
{
  "user_id": "uuid",
  "access_token": "jwt...",
  "refresh_token": "jwt..."
}
```

**Backend implementation:**
1. Exchange `code` with Google at `https://oauth2.googleapis.com/token` using `client_id` + `client_secret` + `redirect_uri=http://localhost:8000/auth/google/callback`
2. Fetch user info from `https://www.googleapis.com/oauth2/v2/userinfo` with the Google access token
3. Find or create user by Google email
4. Return your own JWT tokens (same format as `/auth/login`)

**Google OAuth scopes requested by desktop:** `openid email profile`

**Redirect URI configured in desktop:** `http://localhost:8000/auth/google/callback`
(Desktop intercepts the redirect before it actually hits the server — only the code is sent via POST)

---

## 5. `GET /auth/me` (optional but useful)

Validates bearer token, returns user profile. Useful for "Logged in as..." in the UI.

**Request:** Bearer token in `Authorization` header

**Response (200):**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "avatar_url": "https://..."
}
```

---

## 6. `POST /auth/link-telegram`

Telegram bot `/link` command connects a Telegram user to their Planly account.

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
  "user_id": "uuid"
}
```

**Response (404):**
```json
{
  "detail": "No account found with that email"
}
```

---

## 7. `POST /agent/process`

Main endpoint. Desktop sends user's typed command + OCR'd screenshot data.

**Request:**
```json
{
  "source": "desktop_screenshot",
  "conversation_id": "uuid | null",
  "user_prompt": "appoint dinner tomorrow at 7pm",
  "context": {
    "messages": [
      {"username": "Alice", "text": "Let's do dinner tomorrow", "timestamp": "2:30 PM"},
      {"username": "Bob", "text": "Sure, 7pm works", "timestamp": "2:31 PM"}
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
- `conversation_id` (string | null) — pass from previous response for multi-turn
- `context.messages` — OCR-parsed chat messages from the screenshot
- `context.screenshot_metadata.raw_text` — full OCR dump for validation

**Response (200) — must return `blocks[]` array:**
```json
{
  "conversation_id": "uuid",
  "blocks": [
    {"type": "text", "content": "I see a dinner plan. Let me help organize that."},
    {
      "type": "action_cards",
      "actions": [
        {
          "action_id": "uuid",
          "tool": "calendar_create_event",
          "description": "Create calendar event 'Dinner' on Feb 9 at 7pm",
          "parameters": {"title": "Dinner", "datetime": "2026-02-09T19:00:00Z"}
        }
      ]
    }
  ]
}
```

**Block types the frontend renders:**

| Type | Fields | When to use |
|---|---|---|
| `text` | `content: string` | Any text response |
| `action_cards` | `actions: Action[]` | Proposed actions for user to select/confirm |
| `calendar_picker` | `prompt: string` | Agent needs a date from user |
| `time_picker` | `prompt: string` | Agent needs a time from user |
| `error` | `message: string` | Something went wrong |

**Screenshot validation:** If the screenshot is not useful (no conversation, wrong app), return a `text` block asking for clarification. The user will reply in the same conversation.

**Multi-turn:** When `conversation_id` is provided, look up previous context from database, append new prompt + messages, continue the conversation (not start fresh).

This enables flows like:
- User: "appoint dinner" -> Agent: "When?" -> (calendar_picker) -> User: "2026-02-10" -> Agent returns action_cards

---

## 8. `POST /agent/confirm-actions`

User selects action cards and hits Confirm. Desktop sends the selected action IDs.

**Request:**
```json
{
  "conversation_id": "uuid",
  "action_ids": ["action-uuid-1", "action-uuid-2"]
}
```

**Response (200):**
```json
{
  "results": [
    {
      "action_id": "action-uuid-1",
      "tool": "calendar_create_event",
      "success": true,
      "result": {}
    }
  ],
  "formatted_response": "Done! Dinner event created for tomorrow at 7pm."
}
```

---

## Summary

| # | Endpoint | Method | Auth Required |
|---|---|---|---|
| 1 | `/auth/login` | POST | No |
| 2 | `/auth/register` | POST | No |
| 3 | `/auth/refresh` | POST | No |
| 4 | `/auth/google/callback` | POST | No |
| 5 | `/auth/me` | GET | Yes |
| 6 | `/auth/link-telegram` | POST | No |
| 7 | `/agent/process` | POST | Yes |
| 8 | `/agent/confirm-actions` | POST | Yes |
