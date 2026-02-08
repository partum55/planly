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
