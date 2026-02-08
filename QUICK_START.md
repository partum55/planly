# 🚀 Planly Quick Start

## Your Current Status

✅ **Code:** Complete (3,500+ lines)
✅ **Dependencies:** Installed
⚠️ **Setup:** Needs Supabase credentials

---

## 🎯 Get Running in 15 Minutes

### Quick Setup (2 commands - Cloud LLM)

```bash
# 1. Set up Supabase (follow prompts)
./configure_env.sh

# 2. Get Cloud LLM API key
# See CLOUD_LLM_SETUP.md for detailed instructions
# Recommended: Groq (free, fast) or Together AI ($25 free credits)
# Update .env with your API key

# 3. Start server
./run_server.sh
```

### Alternative: Local Ollama Setup

```bash
# 1. Set up Supabase
./configure_env.sh

# 2. Install Ollama and pull model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b

# 3. Update .env: USE_CLOUD_LLM=false

# 4. Start server
./run_server.sh
```

### Detailed Setup (Step-by-step)

Follow: **`SUPABASE_SETUP_CHECKLIST.md`**

It has checkboxes for each step! ✓

---

## 📖 Documentation Map

### Getting Started:
- **`SUPABASE_SETUP_CHECKLIST.md`** ← Start here!
- **`CLOUD_LLM_SETUP.md`** ← Get your LLM API key (Groq/Together AI)
- **`configure_env.sh`** - Interactive setup
- **`run_server.sh`** - Start the server

### Supabase Help:
- **`GET_SUPABASE_CREDENTIALS.md`** - Where to find keys
- **`RUN_DATABASE_SCHEMA.md`** - How to create tables

### Reference:
- **`server/SETUP.md`** - Detailed setup guide
- **`server/README.md`** - Code overview
- **`IMPLEMENTATION_SUMMARY.md`** - What we built

### Testing:
- **`server/test_api.sh`** - Quick API tests
- **http://localhost:8000/docs** - Interactive API docs

---

## 🎬 What to Do RIGHT NOW

### Option 1: Full Setup (Recommended)
```bash
# Open the checklist
cat SUPABASE_SETUP_CHECKLIST.md

# Or open in your editor
code SUPABASE_SETUP_CHECKLIST.md
```

Then follow the 7 steps!

### Option 2: Interactive Setup
```bash
# Run the configuration wizard
./configure_env.sh
```

It will ask you for:
1. Supabase URL
2. Supabase Key

Then automatically configure everything!

---

## ⚡ Common Commands

```bash
# Start server
./run_server.sh

# Configure environment
./configure_env.sh

# Test API
./server/test_api.sh

# View API docs (once running)
open http://localhost:8000/docs

# Check server logs
tail -f server/logs/*.log

# Stop server
# Press Ctrl+C in the terminal where server is running
```

---

## 🎯 The 3 Things You Need

To run the server, you MUST have:

1. **✓ Supabase Credentials**
   - Project URL: `https://xxxxx.supabase.co`
   - Service Role Key: `eyJ...`
   - Get from: Settings → API in Supabase dashboard

2. **✓ Database Schema Loaded**
   - Run `server/database/supabase_schema.sql` in Supabase SQL Editor
   - Creates 7 tables

3. **✓ LLM API Access**

   **Option A: Cloud API (Recommended for Hackathon)**
   - Get free API key from Groq or Together AI
   - See `CLOUD_LLM_SETUP.md` for detailed guide
   - No local installation needed!

   **Option B: Local Ollama**
   ```bash
   ollama serve  # In one terminal
   ollama pull llama3.1:8b  # Downloads model
   ```

---

## 🆘 Having Issues?

### Can't create Supabase project?
- Make sure you're signed in at supabase.com
- Free tier allows 2 projects
- Check your email for verification

### Can't find credentials?
- See: `GET_SUPABASE_CREDENTIALS.md`
- Make sure you copy the `service_role` key, not `anon`

### Schema won't run?
- See: `RUN_DATABASE_SCHEMA.md`
- Copy the ENTIRE `supabase_schema.sql` file
- Run in SQL Editor, not psql (easier)

### Ollama not working?
```bash
# Check if installed
ollama --version

# Start service
ollama serve

# Test
curl http://localhost:11434/api/tags
```

### Server won't start?
```bash
# Check .env file exists and has credentials
cat server/.env | grep SUPABASE_URL

# Check dependencies installed
venv/bin/pip list | grep fastapi

# Check for errors
PYTHONPATH=server venv/bin/python server/main.py
```

---

## 📱 What's Next?

Once your server is running:

1. **✅ Test the API**
   - Visit: http://localhost:8000/docs
   - Try the endpoints in Swagger UI

2. **📱 Build Telegram Bot** (Agent 2)
   - See: `AGENT_2_PROMPT.md`
   - Simple webhook forwarder

3. **💻 Build Desktop App** (Agent 2)
   - See: `AGENT_2_PROMPT.md`
   - Electron app with OCR

---

## 🎉 You're Almost There!

The hard part (coding) is done. Now just:
1. Create Supabase project (10 min)
2. Configure & start (5 min)
3. Start building clients!

**Ready? Open:** `SUPABASE_SETUP_CHECKLIST.md`
