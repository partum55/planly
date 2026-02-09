# Planly

**An AI agent that reads your group chats, understands what everyone wants to do, and makes it happen.**

Planly watches conversations in Telegram groups or on your screen, extracts plans like "let's grab dinner Friday" or "meeting at 3pm tomorrow", and turns them into calendar events, restaurant suggestions, and actionable next steps — all through natural conversation.

## How It Works

```
Observe  →  Reason  →  Plan  →  Act  →  Respond
```

1. **Observe** — Captures messages from Telegram groups or screenshots of any chat app on your desktop
2. **Reason** — An LLM parses the conversation, identifies intent, extracts entities (people, times, places)
3. **Plan** — Determines what actions to take: create events, look up venues, suggest times
4. **Act** — Executes via integrations: Google Calendar, Google Places, Yelp
5. **Respond** — Returns structured results: text, action cards, calendar/time pickers for confirmation

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Clients                               │
│                                                              │
│  ┌─────────────────────┐       ┌──────────────────────────┐  │
│  │   Desktop App        │       │   Telegram Bot           │  │
│  │   (Electron)         │       │   (python-telegram-bot)  │  │
│  │                      │       │                          │  │
│  │  Screenshot → OCR    │       │  Listens to group chats  │  │
│  │  Chat UI overlay     │       │  Forwards messages       │  │
│  └──────────┬──────────┘       └────────────┬─────────────┘  │
│             │                               │                │
└─────────────┼───────────────────────────────┼────────────────┘
              │          HTTP / JSON           │
              ▼                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                         │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────────┐  │
│  │ Auth     │  │ Agent    │  │ Integrations               │  │
│  │ (JWT)    │  │ (LLM)   │  │ Google Calendar · Places    │  │
│  │          │  │          │  │ Yelp · Google Maps          │  │
│  └──────────┘  └──────────┘  └────────────────────────────┘  │
│                      │                                       │
│               ┌──────┴──────┐                                │
│               │  Supabase   │                                │
│               │  (Postgres) │                                │
│               └─────────────┘                                │
└──────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-platform input** — Desktop screenshot+OCR for any chat app, or native Telegram integration
- **Natural language understanding** — Extracts plans, times, locations, and participants from casual conversation
- **Google Calendar integration** — Creates events directly from extracted plans
- **Venue suggestions** — Finds restaurants and places via Google Places and Yelp
- **Multi-turn conversation** — Ask follow-up questions, refine plans, confirm before acting
- **Structured responses** — Rich UI with action cards, calendar pickers, time pickers
- **Cross-platform desktop app** — Linux (AppImage), Windows (installer), macOS (DMG)
- **CI/CD** — GitHub Actions builds and releases for all three platforms

## Project Structure

```
planly/
├── server/                  # FastAPI backend
│   ├── api/                 #   Routes and endpoints
│   ├── config/              #   Settings
│   ├── core/                #   Core agent logic
│   ├── database/            #   Supabase client and schema
│   ├── integrations/        #   Google Calendar, Places, Yelp
│   ├── models/              #   Pydantic data models
│   ├── services/            #   Business logic services
│   ├── tools/               #   Agent tool definitions
│   ├── main.py              #   Entry point
│   └── .env.example         #   Environment template
│
├── desktop-app/             # Electron desktop client
│   ├── src/
│   │   ├── main.ts          #   Main process (tray, shortcuts, IPC)
│   │   ├── ui/              #   Chat and login HTML
│   │   ├── services/        #   Screenshot, OCR, API client, auth
│   │   └── renderer/        #   Renderer process logic
│   ├── build/               #   App icons
│   ├── package.json
│   └── .env.example         #   Environment template
│
├── telegram-bot/            # Telegram bot client
│   ├── bot.py               #   Main bot application
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example         #   Environment template
│
├── docs/                    # Setup guides, specs, deployment docs
├── .github/workflows/       # CI — desktop app build + release
└── LICENSE                  # MPL-2.0
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- A [Supabase](https://supabase.com) project (free tier works)
- An LLM endpoint ([Ollama](https://ollama.ai) for local, or any OpenAI-compatible API)

### 1. Server

```bash
cd server
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — fill in Supabase credentials, LLM endpoint, and API keys
```

Set up the database by running `server/database/supabase_schema.sql` in your Supabase SQL Editor (see [docs/RUN_DATABASE_SCHEMA.md](docs/RUN_DATABASE_SCHEMA.md) for details).

Start the server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Telegram Bot

```bash
cd telegram-bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — add your Telegram bot token (from @BotFather) and server URL
```

Run the bot:

```bash
python bot.py
```

### 3. Desktop App

**From a release (recommended):**

Download the latest release from [GitHub Releases](../../releases) — available as AppImage (Linux), installer (Windows), or DMG (macOS).

**From source:**

```bash
cd desktop-app
npm install

cp .env.example .env
# Edit .env — set WEBSERVER_URL to your running server

npm run dev
```

Build distributable packages:

```bash
npm run build    # Creates AppImage / .exe / .dmg depending on your OS
```

> **Linux/Wayland note:** Launch with `ELECTRON_DISABLE_SANDBOX=1 npx electron . --no-sandbox` if you hit sandbox errors. The global shortcut uses a GNOME custom keybinding — see [docs/QUICK_START.md](docs/QUICK_START.md).

## Environment Variables

Each component has a `.env.example` with all available options. Key variables:

| Variable | Component | Description |
|---|---|---|
| `SUPABASE_URL` | Server | Supabase project URL |
| `SUPABASE_KEY` | Server | Supabase anon/service key |
| `OLLAMA_ENDPOINT` | Server | LLM API endpoint |
| `OLLAMA_MODEL` | Server | Model name (e.g. `llama3`) |
| `GOOGLE_CALENDAR_ID` | Server | Target calendar ID |
| `JWT_SECRET_KEY` | Server | Secret for auth tokens |
| `TELEGRAM_BOT_TOKEN` | Bot | Token from @BotFather |
| `WEBSERVER_URL` | Bot, Desktop | Backend API URL |
| `GOOGLE_CLIENT_ID` | Desktop | OAuth client ID |

See the `.env.example` in each directory for the full list.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| Database | Supabase (PostgreSQL) |
| LLM | Ollama / OpenAI-compatible API |
| Desktop | Electron, TypeScript, Tesseract.js |
| Telegram | python-telegram-bot |
| Integrations | Google Calendar, Google Places, Yelp, Google Maps |
| CI/CD | GitHub Actions |
| Auth | JWT (bcrypt + PyJWT) |

## Documentation

Additional setup guides and references are in the [`docs/`](docs/) folder:

- [API Specification](docs/API_SPECIFICATION.md)
- [Quick Start](docs/QUICK_START.md)
- [Supabase Setup](docs/SUPABASE_SETUP_CHECKLIST.md)
- [Cloud LLM Setup](docs/CLOUD_LLM_SETUP.md)
- [Google OAuth Setup](docs/GOOGLE_OAUTH_SETUP.md)
- [Deployment (DigitalOcean)](docs/DEPLOYMENT_DIGITALOCEAN.md)

## License

[Mozilla Public License 2.0](LICENSE)

## Credits

Built during a hackathon by two AI-assisted agents working in parallel — one on the backend, one on the frontend.
