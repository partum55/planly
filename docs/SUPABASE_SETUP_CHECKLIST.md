# ✅ Supabase Setup Checklist

Follow these steps in order to get your Planly server running!

---

## 📋 Step-by-Step Setup

### ☐ Step 1: Create Supabase Project (5 minutes)

1. **Visit:** https://supabase.com
2. **Sign in** with GitHub or email
3. **Click** "New Project"
4. **Fill in:**
   - Name: `planly`
   - Database Password: (choose strong password - save it!)
   - Region: (closest to you)
5. **Click** "Create new project"
6. **Wait** ~2 minutes for project to be ready

**✓ Check:** You see your project dashboard

---

### ☐ Step 2: Get Your Credentials (2 minutes)

#### Get Project URL:
1. Look at your browser URL bar
2. You'll see: `https://app.supabase.com/project/xxxxxxxxxxxx`
3. Your Project URL is: `https://xxxxxxxxxxxx.supabase.co`
4. **Save this!**

#### Get Service Role Key:
1. Click **"Settings"** (gear icon) in left sidebar
2. Click **"API"**
3. Scroll to **"Project API keys"**
4. Find the **`service_role`** key (NOT the `anon` key!)
5. Click **"Copy"**
6. **Save this!** (It's a long string starting with `eyJ...`)

**📄 Need help?** See `GET_SUPABASE_CREDENTIALS.md`

**✓ Check:** You have both URL and service_role key saved

---

### ☐ Step 3: Run Database Schema (3 minutes)

1. **In Supabase dashboard**, click **"SQL Editor"** (left sidebar)
2. **Click** "New query" button
3. **Open file** `server/database/supabase_schema.sql` on your computer
4. **Copy** all contents (Ctrl+A, Ctrl+C)
5. **Paste** into Supabase SQL Editor
6. **Click** "Run" (or press Ctrl+Enter)
7. **Wait** for success message

#### Verify Tables Created:
1. Click **"Table Editor"** in left sidebar
2. **Check** you see these 7 tables:
   - ✅ users
   - ✅ user_sessions
   - ✅ conversations
   - ✅ messages
   - ✅ events
   - ✅ agent_actions
   - ✅ desktop_screenshots

**📄 Need help?** See `RUN_DATABASE_SCHEMA.md`

**✓ Check:** All 7 tables are visible in Table Editor

---

### ☐ Step 4: Configure Environment (1 minute)

#### Option A: Use Interactive Script (Easiest)

```bash
./configure_env.sh
```

Follow the prompts and paste your credentials.

#### Option B: Edit Manually

```bash
nano server/.env
# or
code server/.env
```

Update these two lines:
```bash
SUPABASE_URL=https://your-actual-project-id.supabase.co
SUPABASE_KEY=eyJhbGc... (your actual service_role key)
```

**✓ Check:** `server/.env` has your real credentials

---

### ☐ Step 5: Install & Start Ollama (3 minutes)

#### Check if already installed:
```bash
ollama --version
```

#### If not installed:

**Linux/Mac:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from https://ollama.com/download

#### Pull the model:
```bash
ollama pull llama3.1:8b
```

This downloads ~4.7GB (takes 2-5 minutes depending on internet)

#### Verify it works:
```bash
ollama run llama3.1:8b "Hello!"
```

Should get a response back. Press Ctrl+D to exit.

#### Start Ollama service:
```bash
ollama serve
```

Leave this running in a terminal.

**✓ Check:** `curl http://localhost:11434/api/tags` returns JSON

---

### ☐ Step 6: Start the Server (30 seconds)

```bash
./run_server.sh
```

You should see:
```
╔════════════════════════════════════════╗
║         Planly Server Starting         ║
╠════════════════════════════════════════╣
║  Address: http://0.0.0.0:8000          ║
║  Docs: http://0.0.0.0:8000/docs        ║
║  LLM: llama3.1:8b                      ║
╚════════════════════════════════════════╝

✓ Supabase client initialized
FastAPI application created
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**✓ Check:** Server starts without errors

---

### ☐ Step 7: Test the API (2 minutes)

#### Test 1: Health Check
```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status":"ok","version":"1.0.0","service":"planly-api"}
```

#### Test 2: Interactive Docs
Open in browser: http://localhost:8000/docs

You should see Swagger UI with all API endpoints.

#### Test 3: Register User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'
```

Expected: JSON response with `access_token`

**✓ Check:** All tests pass

---

## 🎉 Success!

If all steps are checked, your Planly server is running!

### What You Have Now:

✅ **Backend Server** running on http://localhost:8000
✅ **Database** ready in Supabase
✅ **LLM** ready with Ollama
✅ **API** accessible and documented

### Next Steps:

1. **Test all endpoints** via http://localhost:8000/docs
2. **Build Telegram bot client** (Agent 2)
3. **Build Desktop app** (Agent 2)

---

## 🆘 Troubleshooting

### Server won't start:
```bash
# Check logs
cat server/logs/*.log

# Check .env file
cat server/.env | grep SUPABASE

# Test Supabase connection
curl -X GET "https://your-project.supabase.co/rest/v1/" \
  -H "apikey: your-service-role-key"
```

### Database errors:
- Verify all 7 tables exist in Supabase Table Editor
- Re-run the schema if tables are missing
- Check SUPABASE_KEY is the `service_role` key, not `anon`

### Ollama errors:
```bash
# Check if running
curl http://localhost:11434/api/tags

# Restart
pkill ollama
ollama serve

# Re-pull model
ollama pull llama3.1:8b
```

---

## 📚 Documentation

- **Main Setup Guide:** `server/SETUP.md`
- **API Documentation:** http://localhost:8000/docs
- **Implementation Summary:** `IMPLEMENTATION_SUMMARY.md`
- **Get Credentials:** `GET_SUPABASE_CREDENTIALS.md`
- **Database Schema:** `RUN_DATABASE_SCHEMA.md`

---

**Need Help?**
- Check the troubleshooting section above
- Review the detailed guides in the `docs/` folder
- Make sure all prerequisites are installed

**Ready to test?**
```bash
# Quick test script
./server/test_api.sh
```
