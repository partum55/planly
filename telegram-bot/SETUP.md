# Telegram Bot Setup Guide

## Prerequisites

| What | Why | Time |
|------|-----|------|
| Python 3.11+ | Runtime | already installed |
| Telegram Bot Token | Bot identity | ~2 min |
| Running backend (`server/`) | API calls | ~5 min |
| Supabase project | Backend database | ~10 min (if not done) |
| Ollama or cloud LLM | Agent reasoning | ~5 min |

Total first-time setup: **~20 minutes**

---

## Step 1: Create the Telegram Bot (~2 min)

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose a display name (e.g. `Planly`)
4. Choose a username (e.g. `planly_dev_bot`) — must end with `bot`
5. Copy the token BotFather gives you

**Important bot settings** (send these to @BotFather):
```
/setprivacy -> Disable
```
This lets the bot see all group messages, not just commands and @mentions.
Without this, message buffering won't work.

---

## Step 2: Configure Environment (~1 min)

```bash
cd telegram-bot
cp .env.example .env
```

Edit `.env`:
```ini
TELEGRAM_BOT_TOKEN=7123456789:AAH...your-token-from-botfather
WEBSERVER_URL=http://localhost:8000
SERVICE_TOKEN=
```

**About `SERVICE_TOKEN`** — see [Auth Section](#auth-how-the-bot-authenticates-with-the-backend) below.

---

## Step 3: Install Dependencies (~1 min)

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install "python-telegram-bot>=20.7" "httpx>=0.26.0" "python-dotenv>=1.0.0"
```

---

## Step 4: Start the Backend (~5 min)

The bot calls two backend endpoints that require JWT auth:
- `POST /agent/process` — main agent processing
- `POST /agent/confirm-actions` — execute confirmed actions

Make sure the backend is running:
```bash
cd server
cp .env.example .env   # fill in Supabase + JWT_SECRET_KEY + LLM config
pip install -r requirements.txt
python main.py
```

Verify: `curl http://localhost:8000/health` should return `{"status": "ok"}`.

---

## Step 5: Start the Bot (~30 sec)

```bash
cd telegram-bot
python3 bot.py
```

Expected output:
```
Planly Telegram bot started
Backend: http://localhost:8000
Auth: SERVICE_TOKEN set       # or "no auth" if token is empty
```

---

## Step 6: Add Bot to a Group (~1 min)

1. Create a Telegram group (or use existing)
2. Add the bot as a member
3. Send some messages to build up the buffer
4. Mention the bot: `@planly_dev_bot book dinner tomorrow at 7pm`
5. Bot sends typing indicator, calls backend, replies with action cards

---

## Auth: How the Bot Authenticates with the Backend

### The Problem

`/agent/process` and `/agent/confirm-actions` require a valid JWT Bearer token.
The backend's auth middleware (`get_current_user`) decodes the JWT, extracts `user_id`,
and verifies the user exists in the database.

A plain `SERVICE_TOKEN` string **will not work** — it must be a valid JWT.

### Solution: Generate a JWT for the Bot

**Option A — Register a bot service account (recommended for hackathon):**

```bash
# Register a Planly account for the bot
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "bot@planly.local", "password": "service-bot-password", "full_name": "Planly Bot"}'
```

Response:
```json
{"user_id": "uuid", "access_token": "eyJ...", "refresh_token": "..."}
```

Copy the `access_token` into `.env`:
```ini
SERVICE_TOKEN=eyJ...the-full-jwt-token
```

**Limitation:** Access tokens expire in 60 minutes (configurable via
`ACCESS_TOKEN_EXPIRE_MINUTES` in `server/.env`). For the hackathon, set it
to a large value like `525600` (1 year) in the backend's `.env`:
```ini
ACCESS_TOKEN_EXPIRE_MINUTES=525600
```

**Option B — Agent 1 adds service token bypass (production path):**

Add to `server/api/middleware/auth_middleware.py`:
```python
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "")

async def get_current_user(...):
    token = credentials.credentials
    if SERVICE_TOKEN and token == SERVICE_TOKEN:
        return {"id": "service-bot-uuid", "is_active": True}
    # ... existing JWT decode logic
```

This is the cleaner long-term fix — documented in AGENT_1_TASKS.md if needed.

**Option C — No auth (leave SERVICE_TOKEN empty):**

The bot will send requests without an Authorization header.
The backend will reject them with 401. Only useful if you're testing
the bot UI in isolation without a running backend.

---

## How the Pieces Connect

```
┌─────────────────┐         ┌──────────────────┐         ┌───────────────┐
│  Telegram Group  │────────>│  Telegram Bot     │────────>│  Backend API  │
│                  │ messages│  (bot.py)         │ HTTP    │  (server/)    │
│  Users chat     │<────────│                   │<────────│               │
│  @mention bot   │ replies │  Buffers messages  │ blocks  │  /agent/*     │
└─────────────────┘         │  Detects @mention  │         │  JWT auth     │
                            │  Renders blocks    │         │  ORPLAR loop  │
                            │  Inline keyboards  │         │  LLM + tools  │
                            └──────────────────┘         └───────────────┘

┌─────────────────┐         ┌──────────────────┐              │
│  Desktop App     │────────>│  Electron         │─────────────┘
│  Ctrl+Alt+J     │ shortcut│  (desktop-app/)   │  Same /agent/* endpoints
│  Screenshot+OCR │<────────│  api-client.ts    │  Same JWT auth
└─────────────────┘ blocks  │  chat.html        │  Same block rendering
                            └──────────────────┘
```

### Endpoint Map

| Client | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| Desktop | `POST /agent/process` | JWT (user login) | Process screenshot + prompt |
| Desktop | `POST /agent/confirm-actions` | JWT (user login) | Execute selected actions |
| Bot | `POST /agent/process` | JWT (service token) | Process buffered messages + prompt |
| Bot | `POST /agent/confirm-actions` | JWT (service token) | Execute selected actions |
| Bot | `POST /auth/link-telegram` | None | Link Telegram user to Planly account |
| Both | `GET /health` | None | Health check |

### Request Payload Differences

**Desktop** sends to `/agent/process`:
```json
{
  "source": "desktop_screenshot",
  "context": {
    "messages": [/* OCR-parsed from screenshot */],
    "screenshot_metadata": {"ocr_confidence": 85.5, "raw_text": "..."}
  }
}
```

**Bot** sends to `/agent/process`:
```json
{
  "source": "telegram",
  "context": {
    "messages": [/* buffered from group chat, last 50 */],
    "screenshot_metadata": {"ocr_confidence": 100.0, "raw_text": "joined buffer"}
  }
}
```

Both use the same `AgentProcessRequest` schema — fully compatible.

---

## Legacy Endpoint: `/telegram/webhook`

The backend also has `POST /telegram/webhook` (no auth). The **old** bot used this.
It stores messages and returns `{response_text: string}` on @mention.

The **new** bot does NOT use this endpoint. It uses `/agent/process` instead to get
rich `blocks[]` responses (action cards, pickers, etc.) matching the desktop app flow.

The webhook endpoint still exists and works but returns plain text only — no
inline keyboards, no action card selection.

---

## Bot Commands Reference

| Command | What it does |
|---------|-------------|
| `/start` | Welcome message with usage instructions |
| `/help` | Detailed usage guide |
| `/link <email>` | Connect Telegram account to Planly (calls `/auth/link-telegram`) |
| `/reset` | Clear message buffer, conversation ID, and action state for this group |

---

## How Message Buffering Works

1. Every text message in the group is silently stored in a `deque(maxlen=50)`
2. When someone @mentions the bot, the buffer is sent as context to `/agent/process`
3. The backend's LLM uses this context to understand what the group is planning
4. Buffer persists per `chat_id` — separate groups have separate buffers
5. `/reset` clears the buffer

**Note:** Buffers are in-memory only. They reset when the bot restarts.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Bot doesn't see group messages | Privacy mode enabled | Send `/setprivacy` → Disable to @BotFather |
| `Backend error: Invalid or expired token` | SERVICE_TOKEN is not a valid JWT | Generate one via `/auth/register` (see Auth section) |
| `Could not reach the Planly server` | Backend not running | Start with `cd server && python main.py` |
| Bot replies to every message | `_is_mention` broken | Check bot username matches `@your_bot_name` |
| Action cards don't work | Backend returns empty blocks | Check LLM is running (Ollama or cloud) |
| `This action card has expired` | Different message_id | Someone clicked old buttons — mention bot again |
| Confirm shows error | Action plan cache cleared | Backend restarted — mention bot again to regenerate |
