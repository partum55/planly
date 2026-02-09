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

---

# Deploy to DigitalOcean App Platform

The bot uses long-polling (`run_polling()`), not webhooks. On DigitalOcean App Platform
this means it must run as a **Worker** (background process), not a Web Service.

**Total time: ~15 minutes** (first deploy)

---

## Prerequisites (~2 min)

| What | Status | Notes |
|------|--------|-------|
| DigitalOcean account | needed | [cloud.digitalocean.com](https://cloud.digitalocean.com) |
| `doctl` CLI | optional | can use web dashboard instead |
| GitHub repo with `telegram-bot/` pushed | needed | DO pulls from git |
| Backend deployed & reachable | needed | bot needs `WEBSERVER_URL` that's not `localhost` |
| `SERVICE_TOKEN` (valid JWT) | needed | see [Auth section](#auth-how-the-bot-authenticates-with-the-backend) |

**Important:** Your backend must be reachable from the internet. If the backend is also
on DigitalOcean App Platform, use its public URL (e.g. `https://planly-api-xxxxx.ondigitalocean.app`).

---

## Option A: Deploy via Web Dashboard (~10 min)

### A1. Push code to GitHub (~2 min)

Make sure `telegram-bot/` is in your repo with these files:
```
telegram-bot/
  bot.py
  requirements.txt
  Dockerfile
```

### A2. Create App (~3 min)

1. Go to [cloud.digitalocean.com/apps](https://cloud.digitalocean.com/apps)
2. Click **Create App**
3. Select **GitHub** as source
4. Authorize DigitalOcean to access your repo
5. Select your `planly` repository and branch (`main`)

### A3. Configure as Worker (~2 min)

On the Resources screen:

1. DigitalOcean auto-detects components. **Delete any auto-detected web services.**
2. Click **Add Resource** > **Detect from source code** (or **Create Resource from Dockerfile**)
3. Set:
   - **Name:** `telegram-bot`
   - **Type:** **Worker** (not Web Service)
   - **Source Directory:** `/telegram-bot`
   - **Dockerfile Path:** `/telegram-bot/Dockerfile`
4. **Plan:** Basic ($5/mo) is enough — the bot uses <50MB RAM

### A4. Set Environment Variables (~2 min)

In the app settings, add these env vars for the `telegram-bot` worker:

| Variable | Value | Encrypt? |
|----------|-------|----------|
| `TELEGRAM_BOT_TOKEN` | `7123456789:AAH...` | Yes |
| `WEBSERVER_URL` | `https://your-backend-url.ondigitalocean.app` | No |
| `SERVICE_TOKEN` | `eyJ...valid-jwt` | Yes |

**Do not set these in `.env` file** — App Platform injects them as real environment
variables. The bot's `load_dotenv()` + `os.getenv()` picks them up automatically.

### A5. Deploy (~2 min)

Click **Create Resources**. DigitalOcean will:
1. Pull your repo
2. Build the Docker image
3. Start the worker

Check the **Runtime Logs** tab. You should see:
```
Planly Telegram bot started
Backend: https://your-backend-url.ondigitalocean.app
Auth: SERVICE_TOKEN set
```

---

## Option B: Deploy via `doctl` CLI (~8 min)

### B1. Install doctl (~2 min)

```bash
# Ubuntu/Debian
sudo snap install doctl

# macOS
brew install doctl

# Auth
doctl auth init
```

### B2. Create App Spec (~1 min)

Create `telegram-bot/.do/app.yaml`:

```yaml
name: planly-telegram-bot
region: ams
workers:
  - name: telegram-bot
    dockerfile_path: /telegram-bot/Dockerfile
    source_dir: /telegram-bot
    github:
      repo: your-github-username/planly
      branch: main
      deploy_on_push: true
    instance_count: 1
    instance_size_slug: apps-s-1vcpu-0.5gb
    envs:
      - key: TELEGRAM_BOT_TOKEN
        value: "your-bot-token"
        type: SECRET
      - key: WEBSERVER_URL
        value: "https://your-backend-url.ondigitalocean.app"
      - key: SERVICE_TOKEN
        value: "your-jwt-token"
        type: SECRET
```

### B3. Deploy (~5 min)

```bash
doctl apps create --spec telegram-bot/.do/app.yaml
```

Check status:
```bash
doctl apps list
doctl apps logs <app-id> --type run
```

---

## Verifying the Deploy (~1 min)

1. Open **Runtime Logs** in the DO dashboard (or `doctl apps logs`)
2. Look for `Planly Telegram bot started`
3. Go to your Telegram group
4. Send a test message, then `@your_bot mention something`
5. Bot should reply with typing indicator then agent response

---

## Updating After Code Changes (~2 min)

If `deploy_on_push: true` is set, just push to `main`:
```bash
git add telegram-bot/bot.py
git commit -m "Update bot logic"
git push
```

DigitalOcean auto-redeploys. Takes ~1-2 minutes.

For manual redeploy:
```bash
# Dashboard: Apps > your app > Actions > Force Rebuild
# CLI:
doctl apps create-deployment <app-id> --force-rebuild
```

---

## Cost

| Resource | Plan | Cost |
|----------|------|------|
| Worker (1 instance) | Basic | **$5/month** |
| Bandwidth | 1TB included | $0 |

The bot idles most of the time (long-polling waits for Telegram updates).
Basic plan is more than enough.

---

## Common Deploy Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Build fails | Wrong Dockerfile path | Set Source Directory to `/telegram-bot` |
| Worker crashes immediately | Missing env vars | Check all 3 env vars are set in App Settings |
| `Could not reach the Planly server` | Backend URL is `localhost` | Use the public URL of your deployed backend |
| `Backend error: Invalid or expired token` | JWT expired | Generate a new one, update `SERVICE_TOKEN` env var |
| Bot runs twice / duplicate replies | Multiple instances | Set `instance_count: 1` — polling bots must be single-instance |
| Logs say nothing | Worker type wrong | Must be **Worker**, not Web Service (web expects an HTTP port) |

---

## Why Worker, Not Web Service?

The bot uses `run_polling()` — it opens a persistent connection to Telegram's API
and pulls updates in a loop. It never listens on an HTTP port.

DigitalOcean Web Services expect your process to bind to `$PORT` and serve HTTP.
If you deploy the bot as a Web Service, DO will think it crashed (no port open)
and restart it in a loop.

**Worker** = background process with no port requirement. Exactly what a polling bot needs.
