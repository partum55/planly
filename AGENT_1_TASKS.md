# Agent 1 Tasks: API Changes Required by Agent 2

These changes are needed for the Desktop App and Telegram Bot to work with the backend.

---

## 1. Add `user_prompt` field to `/agent/process`

The desktop app sends the user's typed command along with the screenshot data.

**Updated request body:**
```json
{
  "source": "desktop_screenshot",
  "conversation_id": "uuid | null",
  "user_prompt": "appoint dinner tomorrow at 7pm",
  "context": {
    "messages": [
      {"username": "Alice", "text": "...", "timestamp": "..."}
    ],
    "screenshot_metadata": {
      "ocr_confidence": 85.5,
      "raw_text": "full OCR text..."
    }
  }
}
```

**New fields:**
- `user_prompt` (string, required) — the user's typed command/intent
- `conversation_id` (string, optional) — for multi-turn: pass the ID from previous response to continue
- `context.screenshot_metadata.raw_text` (string, optional) — full OCR text for validation

---

## 2. Widget Response Block Protocol

The backend must return a `blocks` array instead of flat `intent` + `proposed_actions`.

**Updated response for `/agent/process`:**
```json
{
  "conversation_id": "uuid",
  "blocks": [
    { "type": "text", "content": "I see a dinner plan. Let me help organize that." },
    {
      "type": "action_cards",
      "actions": [
        {
          "action_id": "uuid",
          "tool": "calendar_create_event",
          "description": "Create calendar event 'Dinner' on Feb 9 at 7pm",
          "parameters": { "title": "Dinner", "datetime": "2026-02-09T19:00:00Z" }
        }
      ]
    }
  ]
}
```

**Block types the frontend supports:**

| Type | Fields | When to use |
|---|---|---|
| `text` | `content: string` | Any text response from the agent |
| `action_cards` | `actions: Action[]` | When agent proposes actions for user to select |
| `calendar_picker` | `prompt: string` | When agent needs a date from the user |
| `time_picker` | `prompt: string` | When agent needs a time from the user |
| `error` | `message: string` | When something went wrong |

---

## 3. Screenshot Validation

When the model determines the screenshot is **not useful** (no recognizable conversation, wrong app, etc.), return a `text` block asking the user for clarification:

```json
{
  "conversation_id": "uuid",
  "blocks": [
    {
      "type": "text",
      "content": "I couldn't read a conversation from the screenshot. Could you describe who's joining and when?"
    }
  ]
}
```

The user will reply in the chat, triggering another `/agent/process` call with the same `conversation_id`.

---

## 4. Multi-turn Conversation Support

When `conversation_id` is provided, the backend should:
1. Look up previous conversation context from the database
2. Append the new `user_prompt` and any new OCR messages
3. Continue the conversation (not start fresh)

This enables flows like:
- User: "appoint dinner" → Agent: "When?" → (calendar picker) → User: "2026-02-10" → Agent returns action cards

---

## 5. Add `POST /auth/link-telegram` endpoint

The Telegram bot has a `/link` command that connects a Telegram user to their Planly account.

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

## 6. Add `POST /auth/google/callback` endpoint (Google OAuth)

The desktop app now has a "Continue with Google" button. It opens a Google OAuth consent window, captures the authorization code, and sends it to the backend to exchange for tokens.

**Flow:**
1. Desktop opens `https://accounts.google.com/o/oauth2/v2/auth` with `response_type=code`
2. User consents, Google redirects with `?code=...`
3. Desktop captures the code and POSTs it to your backend
4. Backend exchanges the code with Google for user info, creates/finds the user, returns tokens

**Request:**
```json
{
  "code": "4/0AX4XfWh..."
}
```

**Response (200):**
```json
{
  "access_token": "jwt...",
  "refresh_token": "jwt...",
  "user_id": "uuid"
}
```

**Backend implementation:**
- Exchange `code` with Google using `client_id` + `client_secret` + `redirect_uri` via `https://oauth2.googleapis.com/token`
- Get user profile from `https://www.googleapis.com/oauth2/v2/userinfo` using the Google access token
- Find or create user by Google email
- Return your own JWT `access_token` + `refresh_token` (same format as `/auth/login`)

**Google OAuth scopes requested by desktop:** `openid email profile`

**Redirect URI configured in desktop:** `http://localhost:8000/auth/google/callback`
(This is only used for code interception — the desktop app intercepts before the actual redirect happens)

---

## 7. Add `GET /auth/me` endpoint (optional but useful)

Returns the current user's profile based on the bearer token. Useful for showing "Logged in as..." in the UI.

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

## Summary of Changes

1. `POST /agent/process` — add `user_prompt`, `conversation_id`, `raw_text` fields
2. `POST /agent/process` — return `blocks[]` array instead of flat response
3. Support 5 block types: `text`, `action_cards`, `calendar_picker`, `time_picker`, `error`
4. Multi-turn: reuse `conversation_id` for follow-up messages
5. New endpoint: `POST /auth/link-telegram`
6. **New endpoint: `POST /auth/google/callback`** — Google OAuth code exchange, returns JWT tokens
7. **New endpoint: `GET /auth/me`** — returns user profile from bearer token (optional)
