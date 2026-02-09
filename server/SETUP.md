# Planly Server Setup Guide

## Prerequisites

- Python 3.10 or higher
- Supabase account
- LLM API access (Cloud API or local Ollama)
- Google Cloud project (optional, for Calendar API)

---

## Step 1: Environment Setup

### 1.1 Create Virtual Environment

```bash
cd server
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 1.2 Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2: Supabase Database Setup

### 2.1 Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Click "New Project"
3. Choose organization and region
4. Set database password (save it!)
5. Wait for project to be ready

### 2.2 Run Database Schema

1. In Supabase dashboard, go to "SQL Editor"
2. Open `database/supabase_schema.sql`
3. Copy all SQL and paste into SQL Editor
4. Click "Run"
5. Verify tables were created (check "Table Editor")

### 2.3 Get Supabase Credentials

1. Go to Project Settings → API
2. Copy:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **service_role key** (under "Project API keys" - this is the secret key)

---

## Step 3: LLM Setup

### Option A: Cloud API (Recommended)

Fastest and easiest setup - no local installation needed!

1. Choose a provider:
   - **Groq**: Free tier, very fast
   - **Together AI**: Free credits, good reliability
   - **OpenRouter**: Many model options

2. Get your API key:
   - See `CLOUD_LLM_SETUP.md` for detailed instructions

3. Configure in `.env`

```bash
USE_CLOUD_LLM=true
OLLAMA_ENDPOINT=https://api.groq.com/openai  # or together.xyz, openrouter.ai
OLLAMA_MODEL=llama-3.1-8b-instant
LLM_API_KEY=your_api_key_here
```

### Option B: Local Ollama

**For offline use or custom models**

#### 3.1 Install Ollama

```bash
# Linux/Mac:
curl -fsSL https://ollama.com/install.sh | sh

# Windows: Download from https://ollama.com/download
```

#### 3.2 Pull Model

```bash
ollama pull llama3.1:8b

# Verify it's working:
ollama run llama3.1:8b "Hello, how are you?"
```

#### 3.3 Keep Ollama Running

Ollama should be running in the background. If not:

```bash
ollama serve
```

#### 3.4 Configure in `.env`

```bash
USE_CLOUD_LLM=false
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

---

## Step 4: Google Calendar Setup (Optional but Recommended)

### 4.1 Create Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create new project: "Planly"
3. Enable Google Calendar API:
   - APIs & Services → Library
   - Search "Google Calendar API"
   - Click "Enable"

### 4.2 Create Service Account

1. Go to IAM & Admin → Service Accounts
2. Click "Create Service Account"
3. Name: "planly-calendar-service"
4. Grant role: "Editor" (or just Calendar access)
5. Click "Done"
6. Click on the created service account
7. Go to "Keys" tab
8. Click "Add Key" → "Create new key"
9. Choose "JSON"
10. Download the JSON file
11. Save it as: `server/integrations/google_calendar/service_account.json`

### 4.3 Create Shared Calendar

1. Open [Google Calendar](https://calendar.google.com)
2. Create new calendar: "Planly Events"
3. Go to Calendar Settings → Share with specific people
4. Add the service account email (from the JSON file: `client_email`)
5. Give "Make changes to events" permission
6. Copy Calendar ID (Settings → Integrate calendar → Calendar ID)

---

## Step 5: Configure Environment

### 5.1 Create `.env` File

```bash
cp .env.example .env
```

### 5.2 Edit `.env` with Your Credentials

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_service_role_key_here

# LLM Configuration
USE_CLOUD_LLM=true  # Set to false for local Ollama
OLLAMA_ENDPOINT=https://api.groq.com/openai  # or local: http://localhost:11434
OLLAMA_MODEL=llama-3.1-8b-instant  # or local: llama3.1:8b
LLM_API_KEY=your_api_key_here  # Leave empty for local Ollama

# Google Calendar (Optional)
GOOGLE_CALENDAR_ID=your_calendar_id@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_FILE=./integrations/google_calendar/service_account.json

# Auth (IMPORTANT: Change this secret!)
JWT_SECRET_KEY=your_super_secret_random_key_change_this_in_production

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

### 5.3 Generate Secure JWT Secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and use it as `JWT_SECRET_KEY` in `.env`

---

## Step 6: Run the Server

### 6.1 Start Server

```bash
python main.py
```

You should see:
```
╔════════════════════════════════════════╗
║         Planly Server Starting         ║
╠════════════════════════════════════════╣
║  Address: http://0.0.0.0:8000          ║
║  Docs: http://0.0.0.0:8000/docs        ║
║  LLM: [your configured model]          ║
╚════════════════════════════════════════╝
```

### 6.2 Test Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok", "version": "1.0.0", "service": "planly-api"}
```

### 6.3 Open API Documentation

Visit: http://localhost:8000/docs

You should see interactive API documentation (Swagger UI)

---

## Step 7: Test the API

### 7.1 Register a User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "full_name": "Test User"
  }'
```

Save the `access_token` from the response.

### 7.2 Test Agent Processing

```bash
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{
    "source": "desktop_screenshot",
    "context": {
      "messages": [
        {
          "username": "Alice",
          "text": "Lets grab dinner tomorrow at 7pm",
          "timestamp": "2025-03-15T18:00:00Z"
        },
        {
          "username": "Bob",
          "text": "Im in! Italian sounds good",
          "timestamp": "2025-03-15T18:01:00Z"
        }
      ]
    }
  }'
```

You should get back proposed actions!

---

## Troubleshooting

### Database Connection Fails

- Check Supabase URL and key in `.env`
- Verify network connection
- Check if Supabase project is active

### LLM Not Working

#### For Cloud API

```bash
# Check your .env settings
cat server/.env | grep -E "USE_CLOUD_LLM|LLM_API_KEY"

# Verify API key is valid on provider's dashboard
# Check rate limits haven't been exceeded
```

#### For Local Ollama

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it:
ollama serve

# Pull model again if needed:
ollama pull llama3.1:8b
```

### Calendar API Errors

- Verify service account JSON file exists
- Check calendar ID is correct
- Ensure service account has access to the calendar

### Port Already in Use

```bash
# Change PORT in .env to 8001 or another port
PORT=8001
```

---

## Development Tips

### Hot Reload

For development with auto-reload:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Check Logs

Logs will show in the terminal. Increase verbosity:

```bash
LOG_LEVEL=DEBUG
```

### Database Queries

View queries in Supabase:
- Go to Database → Query Performance
- Or use Table Editor to browse data

---

## Next Steps

1. ✅ Server is running
2. Set up Telegram bot client (see `telegram-bot/` directory)
3. Set up Desktop app (see `desktop-app/` directory)
4. Test end-to-end flows

---

## Quick Commands Reference

```bash
# Start server
python main.py

# Install dependencies
pip install -r requirements.txt

# Check LLM (for local Ollama)
ollama list

# Test health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

---

Need help? Check the logs or open an issue!

---

# Deploy to DigitalOcean App Platform

The server is a FastAPI web app — it runs as a **Web Service** on App Platform
(binds to `$PORT`, serves HTTP).

**Total time: ~15 minutes** (first deploy, assuming Supabase + LLM already configured)

---

## Prerequisites (~3 min)

| What | Status | Notes |
|------|--------|-------|
| DigitalOcean account | needed | [cloud.digitalocean.com](https://cloud.digitalocean.com) |
| `doctl` CLI | optional | can use web dashboard instead |
| GitHub repo with `server/` pushed | needed | DO pulls from git |
| Supabase project | needed | cloud DB, already set up from local dev |
| Cloud LLM API key | needed | **can't run Ollama on App Platform** |
| Google Calendar service account | optional | falls back to mock events without it |

**Critical:** Local Ollama will NOT work on App Platform. You must use a cloud
LLM provider (Groq, Together AI, OpenRouter). Set `USE_CLOUD_LLM=true`.

---

## Option A: Deploy via Web Dashboard (~10 min)

### A1. Push code to GitHub (~2 min)

Make sure `server/` is in your repo. Key files:
```
server/
  Dockerfile
  main.py
  requirements.txt
  api/
  core/
  config/
  database/
  integrations/
  models/
  services/
  tools/
  utils/
```

Ensure `.env` is in `.gitignore` — secrets go in DO env vars, not in git.

### A2. Create App (~3 min)

1. Go to [cloud.digitalocean.com/apps](https://cloud.digitalocean.com/apps)
2. Click **Create App**
3. Select **GitHub** as source
4. Authorize DigitalOcean to access your repo
5. Select your `planly` repository and branch (`main`)

### A3. Configure as Web Service (~2 min)

On the Resources screen:

1. DigitalOcean may auto-detect a component. Edit it or create new:
   - **Name:** `planly-api`
   - **Type:** **Web Service**
   - **Source Directory:** `/server`
   - **Dockerfile Path:** `/server/Dockerfile`
2. **HTTP Port:** `8000`
3. **Health Check:** HTTP path `/health`
4. **Plan:** Basic ($5/mo) works for hackathon; Professional ($12/mo) for auto-scaling

### A4. Set Environment Variables (~3 min)

In app settings, add these env vars for the `planly-api` service:

**Required:**

| Variable | Value | Encrypt? |
|----------|-------|----------|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | No |
| `SUPABASE_KEY` | `eyJ...service-role-key` | Yes |
| `USE_CLOUD_LLM` | `true` | No |
| `OLLAMA_ENDPOINT` | `https://api.groq.com/openai` | No |
| `OLLAMA_MODEL` | `llama-3.1-8b-instant` | No |
| `LLM_API_KEY` | `gsk_...your-key` | Yes |
| `JWT_SECRET_KEY` | (generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"`) | Yes |
| `JWT_ALGORITHM` | `HS256` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `525600` | No |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | No |
| `HOST` | `0.0.0.0` | No |
| `PORT` | `8000` | No |
| `LOG_LEVEL` | `INFO` | No |

**Optional (Google Calendar):**

| Variable | Value | Encrypt? |
|----------|-------|----------|
| `GOOGLE_CALENDAR_ID` | `abc@group.calendar.google.com` | No |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | `/app/service_account.json` | No |

For the service account JSON file, see [Google Calendar on DO](#google-calendar-on-digitalocean) below.

### A5. Deploy (~2 min)

Click **Create Resources**. DigitalOcean will:
1. Pull your repo
2. Build the Docker image
3. Start the web service
4. Run health check on `/health`

Once healthy, your API is live at:
```
https://planly-api-xxxxx.ondigitalocean.app
```

Test it:
```bash
curl https://planly-api-xxxxx.ondigitalocean.app/health
# {"status": "ok", "version": "1.0.0", "service": "planly-api"}
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

### B2. Edit App Spec (~1 min)

The spec is already at `server/.do/app.yaml`. Edit the `CHANGE_ME` values:
- `SUPABASE_URL`, `SUPABASE_KEY`
- `LLM_API_KEY`
- `JWT_SECRET_KEY`
- GitHub repo path

### B3. Deploy (~5 min)

```bash
doctl apps create --spec server/.do/app.yaml
```

Check status:
```bash
doctl apps list
doctl apps logs <app-id> --type run
```

---

## Cloud LLM Setup (Required)

App Platform containers can't run Ollama. Use a cloud LLM provider:

### Groq (recommended for hackathon — free, fast)

1. Sign up at [console.groq.com](https://console.groq.com)
2. Create API key
3. Set env vars:
   ```
   USE_CLOUD_LLM=true
   OLLAMA_ENDPOINT=https://api.groq.com/openai
   OLLAMA_MODEL=llama-3.1-8b-instant
   LLM_API_KEY=gsk_...
   ```

### Together AI (free credits)

1. Sign up at [api.together.xyz](https://api.together.xyz)
2. Create API key
3. Set env vars:
   ```
   USE_CLOUD_LLM=true
   OLLAMA_ENDPOINT=https://api.together.xyz
   OLLAMA_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
   LLM_API_KEY=...
   ```

### OpenRouter (many models)

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Create API key
3. Set env vars:
   ```
   USE_CLOUD_LLM=true
   OLLAMA_ENDPOINT=https://openrouter.ai/api
   OLLAMA_MODEL=meta-llama/llama-3.1-8b-instruct
   LLM_API_KEY=sk-or-...
   ```

---

## Google Calendar on DigitalOcean

The calendar client loads a JSON file from `GOOGLE_SERVICE_ACCOUNT_FILE`.
On App Platform there are two approaches:

### Approach 1: Skip it (easiest)

Leave `GOOGLE_CALENDAR_ID` unset. The calendar tool falls back to mock events.
Good enough for hackathon demos.

### Approach 2: Base64-encode as env var (if you need real calendar)

This requires a small code change in `integrations/google_calendar/client.py`:

1. Base64-encode the JSON:
   ```bash
   base64 -w0 integrations/google_calendar/service_account.json
   ```

2. Add env var in DO:
   ```
   GOOGLE_SERVICE_ACCOUNT_JSON=eyJ0eXBlIjoic2VydmljZV9hY...
   ```

3. In `client.py`, add before `_initialize`:
   ```python
   import base64, json, tempfile

   # Decode service account from env var if file doesn't exist
   sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
   if sa_json and not os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_FILE):
       decoded = base64.b64decode(sa_json)
       with open("/app/service_account.json", "w") as f:
           f.write(decoded.decode())
       settings.GOOGLE_SERVICE_ACCOUNT_FILE = "/app/service_account.json"
   ```

---

## Connecting the Telegram Bot to the Deployed Server

Once the server is live, update the telegram bot's env vars:

```
WEBSERVER_URL=https://planly-api-xxxxx.ondigitalocean.app
```

Then generate a SERVICE_TOKEN:
```bash
curl -X POST https://planly-api-xxxxx.ondigitalocean.app/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "bot@planly.local", "password": "service-bot-pw", "full_name": "Planly Bot"}'
```

Copy the `access_token` into the bot's `SERVICE_TOKEN` env var.

---

## Connecting the Desktop App to the Deployed Server

Update the base URL in `desktop-app/src/main.ts` and `desktop-app/src/ui/chat.html`:

```typescript
const API_BASE = 'https://planly-api-xxxxx.ondigitalocean.app';
```

Or make it configurable via environment/settings.

---

## Updating After Code Changes (~2 min)

If `deploy_on_push: true` is set:
```bash
git add server/
git commit -m "Update server"
git push
```

Auto-redeploys in ~2 minutes. Health check verifies `/health` before routing traffic.

For manual redeploy:
```bash
doctl apps create-deployment <app-id> --force-rebuild
```

---

## Cost

| Resource | Plan | Cost |
|----------|------|------|
| Web Service (1 instance) | Basic | **$5/month** |
| Bandwidth | 1TB included | $0 |
| Supabase | Free tier | $0 |
| Groq LLM | Free tier | $0 |

**Hackathon total: $5/month** (or $10 if running bot + server)

---

## Architecture on DigitalOcean

```
                        DigitalOcean App Platform
                    ┌─────────────────────────────────┐
                    │                                  │
Telegram API ──────>│  Worker: telegram-bot ($5/mo)    │
  (polling)  <──────│    bot.py                        │──┐
                    │                                  │  │ HTTPS
                    ├──────────────────────────────────┤  │
                    │                                  │  │
  Desktop App ─────>│  Web Service: planly-api ($5/mo) │<─┘
  (HTTPS)    <─────│    FastAPI + Uvicorn              │
                    │    /agent/process                 │
  Browser    ─────>│    /agent/confirm-actions         │
  (/docs)    <─────│    /auth/*                        │
                    │                                  │
                    └────────────┬─────────────────────┘
                                 │
                    ┌────────────┴─────────────────────┐
                    │     External Services             │
                    │                                   │
                    │  Supabase (DB)     - free tier    │
                    │  Groq (LLM)       - free tier    │
                    │  Google Calendar   - optional     │
                    └───────────────────────────────────┘
```

---

## Common Deploy Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Build fails on `psycopg2` | Missing libpq | Dockerfile includes `libpq-dev` — make sure it's used |
| Health check fails | App not binding to PORT | Ensure `HOST=0.0.0.0` and `PORT=8000` in env vars |
| `Settings validation error` | Missing required env var | `SUPABASE_URL`, `SUPABASE_KEY`, `JWT_SECRET_KEY` are required |
| 500 on `/agent/process` | LLM not reachable | Verify `USE_CLOUD_LLM=true` and `LLM_API_KEY` is valid |
| `Connection refused` from bot | Wrong WEBSERVER_URL | Use the full `https://...ondigitalocean.app` URL |
| CORS errors from desktop | Origins restricted | Backend has `allow_origins=["*"]` — should work. If not, check DO proxy headers |
| Slow first request | Cold start | Basic plan has cold starts. First request after idle may take 5-10s |
| Out of memory | Model too large | Cloud LLM offloads inference — 512MB container should be fine |
