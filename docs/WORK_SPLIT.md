# Work Split: Two Claude Code Agents

## Overview

Split work between **Agent 1 (Backend)** and **Agent 2 (Frontend/Clients)** for parallel development during hackathon.

---

## Agent 1: Webserver Backend (Core AI & API)

**Focus:** Build the central intelligence - webserver with AI agent, tools, and API

### Responsibilities

#### 1. Database & Infrastructure
- [ ] Create `server/` project structure
- [ ] Implement `server/database/supabase_schema.sql` - all tables (users, conversations, messages, events, etc.)
- [ ] Set up `server/database/client.py` - Supabase connection
- [ ] Create repositories:
  - `server/database/repositories/user_repo.py`
  - `server/database/repositories/conversation_repo.py`
  - `server/database/repositories/event_repo.py`

#### 2. Authentication System
- [ ] `server/services/auth_service.py` - registration, login, JWT generation
- [ ] `server/utils/jwt_utils.py` - JWT token utilities
- [ ] `server/api/middleware/auth_middleware.py` - JWT validation

#### 3. Core AI Agent (ORPLAR Loop)
- [ ] `server/core/agent.py` - Main agent orchestrator
- [ ] `server/core/reasoning_engine.py` - LLM integration (Ollama)
- [ ] `server/core/context_manager.py` - Rolling 1-hour context window
- [ ] `server/integrations/ollama/client.py` - Ollama API client
- [ ] `server/integrations/ollama/prompts.py` - LLM prompt templates

#### 4. Tool System
- [ ] `server/tools/base.py` - BaseTool interface, ToolRegistry
- [ ] `server/tools/calendar_tool.py` - Google Calendar integration
- [ ] `server/tools/restaurant_tool.py` - Yelp/Google Places integration
- [ ] `server/tools/cinema_tool.py` - Mock cinema API

#### 5. OCR Integration
- [ ] `server/integrations/ocr/tesseract_processor.py` - OCR for desktop screenshots
- [ ] Parse OCR text into structured messages

#### 6. API Routes (FastAPI)
- [ ] `server/api/app.py` - FastAPI application setup
- [ ] `server/api/routes/auth.py` - Auth endpoints
  - POST /auth/register
  - POST /auth/login
  - POST /auth/refresh
  - POST /auth/link-telegram
- [ ] `server/api/routes/agent.py` - Main agent endpoints
  - POST /agent/process (process conversation, return proposed actions)
  - POST /agent/confirm-actions (execute confirmed actions)
- [ ] `server/api/routes/telegram.py` - Telegram webhook
  - POST /telegram/webhook
- [ ] `server/api/routes/conversations.py` - Conversation management
  - GET /conversations
  - GET /conversations/{id}
- [ ] `server/api/routes/calendar.py` - Calendar operations
  - GET /calendar/events
  - POST /calendar/create
- [ ] `server/api/routes/user.py` - User profile
  - GET /user/profile
  - PATCH /user/profile

#### 7. Configuration & Entry Point
- [ ] `server/config/settings.py` - Environment configuration
- [ ] `server/main.py` - FastAPI entry point
- [ ] `server/.env.example` - Environment variables template
- [ ] `server/requirements.txt` - Python dependencies

#### 8. Testing
- [ ] API endpoint tests
- [ ] Agent logic tests
- [ ] Tool tests

### Dependencies to Set Up
1. Supabase project + database schema
2. Ollama installation and model download
3. Google Calendar service account
4. Yelp/Google Places API keys (optional)

### Deliverables
- Working webserver on `http://localhost:8000`
- All API endpoints functional and tested
- Agent can process conversations and execute tools
- Authentication system working
- Can test with curl/Postman

---

## Agent 2: Clients (Telegram Bot + Desktop App)

**Focus:** Build user-facing interfaces that interact with webserver

### Responsibilities

#### 1. Telegram Bot Client
- [ ] Create `telegram-bot/` project structure
- [ ] `telegram-bot/bot.py` - Main bot script
  - Listen to all group messages
  - Forward to webserver: POST /telegram/webhook
  - Send webserver responses back to Telegram
- [ ] `telegram-bot/config.py` - Configuration
- [ ] `telegram-bot/.env.example` - Bot token and webserver URL
- [ ] `telegram-bot/requirements.txt` - Dependencies

#### 2. Desktop App - Core Setup (Electron)
- [ ] Create `desktop-app/` project structure
- [ ] `desktop-app/main.js` - Electron main process
  - Window management
  - Global keybind registration (Cmd+Shift+P)
- [ ] `desktop-app/preload.js` - Preload script
- [ ] `desktop-app/package.json` - NPM dependencies

#### 3. Desktop App - Screenshot & OCR
- [ ] `desktop-app/src/services/screenshot.js`
  - Capture screenshot on keybind
  - Detect active window (app name, title)
- [ ] `desktop-app/src/services/ocr.js`
  - Tesseract OCR integration
  - Extract text from screenshot
  - Return confidence score

#### 4. Desktop App - API Client
- [ ] `desktop-app/src/services/api-client.js`
  - HTTP client for webserver API
  - POST /agent/process
  - POST /agent/confirm-actions
  - Error handling and retries
- [ ] `desktop-app/src/services/auth.js`
  - Token management (store/retrieve)
  - Login flow
  - Auto-refresh tokens

#### 5. Desktop App - UI (Overlay)
- [ ] `desktop-app/src/overlay.html` - Overlay window HTML
  - Conversation context display
  - Detected intent section
  - Proposed actions with checkboxes
  - Confirm/Cancel buttons
- [ ] `desktop-app/src/styles/overlay.css` - ChatGPT-style styling
- [ ] `desktop-app/src/renderer/overlay.js` - Overlay logic
  - Show/hide overlay
  - Populate with API response
  - Handle user confirmation
  - Display results

#### 6. Desktop App - Components
- [ ] `desktop-app/src/components/ConversationView.js`
  - Display extracted messages
- [ ] `desktop-app/src/components/ActionConfirmation.js`
  - Action list with checkboxes
- [ ] `desktop-app/src/components/NotificationToast.js`
  - Success/error notifications

#### 7. Desktop App - Auth UI
- [ ] `desktop-app/src/login.html` - Login page
- [ ] `desktop-app/src/renderer/login.js` - Login form logic
  - Email/password login
  - Store tokens
  - Redirect to main app

#### 8. Desktop App - Integration
- [ ] Wire up complete flow:
  - Keybind → Screenshot → OCR → API call → Overlay → Confirmation → Results
- [ ] Error handling throughout
- [ ] Loading states

#### 9. Build Configuration
- [ ] `desktop-app/build/` - Build config
- [ ] Electron builder setup
- [ ] Icons and assets

#### 10. Testing
- [ ] E2E tests
- [ ] Manual testing with different chat apps

### Dependencies to Set Up
1. Telegram bot token (via @BotFather)
2. Node.js and npm
3. Electron development tools
4. Tesseract OCR installation

### Deliverables
- Telegram bot that forwards messages to webserver and replies
- Desktop app that:
  - Captures screenshots on keybind
  - Extracts text via OCR
  - Shows beautiful overlay with agent's proposals
  - Handles user confirmation
  - Displays results

---

## Interface Contract (How Agents Coordinate)

### API Endpoints (Agent 1 provides, Agent 2 consumes)

**Base URL:** `http://localhost:8000`

#### 1. Authentication
```
POST /auth/register
Body: { "email": "...", "password": "...", "full_name": "..." }
Response: { "user_id": "...", "access_token": "...", "refresh_token": "..." }

POST /auth/login
Body: { "email": "...", "password": "..." }
Response: { "access_token": "...", "refresh_token": "..." }
```

#### 2. Agent Processing (Desktop App → Webserver)
```
POST /agent/process
Headers: Authorization: Bearer <token>
Body: {
  "source": "desktop_screenshot",
  "context": {
    "messages": [
      {"username": "Alice", "text": "...", "timestamp": "..."},
      {"username": "Bob", "text": "...", "timestamp": "..."}
    ],
    "screenshot_metadata": {
      "window_title": "Discord",
      "app_name": "Discord",
      "ocr_confidence": 0.95
    }
  }
}
Response: {
  "conversation_id": "uuid",
  "intent": {...},
  "proposed_actions": [
    {"action_id": "uuid", "tool": "...", "description": "...", "parameters": {...}}
  ]
}
```

#### 3. Confirm Actions (Desktop App → Webserver)
```
POST /agent/confirm-actions
Headers: Authorization: Bearer <token>
Body: {
  "conversation_id": "uuid",
  "action_ids": ["uuid1", "uuid2"]
}
Response: {
  "results": [
    {"action_id": "uuid1", "success": true, "result": {...}}
  ],
  "formatted_response": "Created calendar event: ..."
}
```

#### 4. Telegram Webhook (Telegram Bot → Webserver)
```
POST /telegram/webhook
Body: {
  "group_id": 123456,
  "message_id": 789,
  "user_id": 111,
  "username": "alice",
  "text": "...",
  "timestamp": "...",
  "is_bot_mention": false
}
Response: {
  "response_text": "..." | null
}
```

### Shared Data Models (Both agents must agree)

#### Message Format
```json
{
  "username": "Alice",
  "text": "Let's get dinner tomorrow",
  "timestamp": "2026-02-08T18:00:00Z"
}
```

#### Intent Format
```json
{
  "activity_type": "restaurant",
  "participants": ["Alice", "Bob"],
  "datetime": "2026-02-09T19:00:00Z",
  "location": "Downtown",
  "confidence": 0.85
}
```

#### Action Format
```json
{
  "action_id": "uuid",
  "tool": "calendar_create_event",
  "description": "Create calendar event 'Dinner' on Feb 9 at 7pm",
  "parameters": {
    "title": "Dinner with Alice and Bob",
    "datetime": "2026-02-09T19:00:00Z",
    "duration_minutes": 120
  }
}
```

---

## Development Workflow

### Phase 1: Setup (Day 1 Morning)
**Both agents:**
- [ ] Agent 1: Set up webserver project structure
- [ ] Agent 2: Set up telegram-bot and desktop-app project structures
- [ ] Both: Share `.env.example` files and coordinate on environment variables

### Phase 2: Core Backend (Day 1 Afternoon)
**Agent 1 focus:**
- [ ] Implement database schema
- [ ] Build authentication system
- [ ] Create basic API routes (auth, agent)

**Agent 2 (can start in parallel):**
- [ ] Build telegram bot basic structure (listening, forwarding)
- [ ] Start desktop app Electron setup
- [ ] Mock API client with dummy responses for testing

### Phase 3: AI Agent (Day 2 Morning)
**Agent 1 focus:**
- [ ] Implement core agent (ORPLAR loop)
- [ ] Build tool system
- [ ] Integrate Ollama
- [ ] Test with curl/Postman

**Agent 2 (can test once Agent 1 ready):**
- [ ] Finish telegram bot integration
- [ ] Build screenshot + OCR functionality
- [ ] Test API client with real webserver

### Phase 4: Integration (Day 2 Afternoon)
**Both agents:**
- [ ] Agent 1: Expose all API endpoints
- [ ] Agent 2: Integrate telegram bot with webserver
- [ ] Agent 2: Build desktop app overlay UI
- [ ] Test end-to-end flows

### Phase 5: Polish (Day 3)
**Agent 1:**
- [ ] Add error handling
- [ ] Write API tests
- [ ] Optimize performance

**Agent 2:**
- [ ] Polish desktop app UI
- [ ] Add error messages and loading states
- [ ] Test with different chat apps
- [ ] Build desktop app for demo

### Phase 6: Demo Prep (Day 4)
**Both agents:**
- [ ] Prepare demo scenarios
- [ ] Write documentation
- [ ] Test presentation flow
- [ ] Record backup demo video

---

## Communication Points

### Regular Sync-Ups
- **Morning standup:** What did you complete? What are you working on today? Any blockers?
- **Afternoon check-in:** Is the API contract working? Any changes needed?

### Key Handoff Points
1. **After Agent 1 completes auth system:** Agent 2 can test login flow
2. **After Agent 1 completes `/agent/process` endpoint:** Agent 2 can integrate desktop app
3. **After Agent 1 completes `/telegram/webhook` endpoint:** Agent 2 can test telegram bot

### Blockers & Dependencies
- **Agent 2 blocked on Agent 1:**
  - Auth endpoints must be ready before desktop login works
  - `/agent/process` must be ready before desktop overlay works
- **Agent 1 can work independently:**
  - Use Postman/curl to test all endpoints
  - Mock client requests

---

## Success Criteria

### Agent 1 Deliverables
✅ Webserver running on localhost:8000
✅ All API endpoints functional
✅ Agent can extract intent from conversation
✅ Tools can execute (calendar, restaurant search)
✅ Authentication working (register, login, JWT)
✅ Can demo with Postman

### Agent 2 Deliverables
✅ Telegram bot forwards messages and replies work
✅ Desktop app captures screenshots on keybind
✅ Desktop app extracts text via OCR
✅ Desktop app shows overlay with agent proposals
✅ Desktop app can confirm and execute actions
✅ Beautiful UI (ChatGPT-style)

### Combined Success
✅ End-to-end Telegram flow works (group chat → bot → webserver → calendar)
✅ End-to-end desktop flow works (screenshot → OCR → webserver → overlay → calendar)
✅ Both clients can see each other's events (synced via webserver)
✅ Ready for hackathon demo

---

## Quick Reference

### Agent 1 Key Files (10 most critical)
1. `server/database/supabase_schema.sql`
2. `server/core/agent.py`
3. `server/core/reasoning_engine.py`
4. `server/tools/base.py`
5. `server/tools/calendar_tool.py`
6. `server/api/routes/agent.py`
7. `server/api/routes/auth.py`
8. `server/services/auth_service.py`
9. `server/integrations/ollama/client.py`
10. `server/main.py`

### Agent 2 Key Files (10 most critical)
1. `telegram-bot/bot.py`
2. `desktop-app/main.js`
3. `desktop-app/src/services/screenshot.js`
4. `desktop-app/src/services/ocr.js`
5. `desktop-app/src/services/api-client.js`
6. `desktop-app/src/overlay.html`
7. `desktop-app/src/renderer/overlay.js`
8. `desktop-app/src/styles/overlay.css`
9. `desktop-app/src/services/auth.js`
10. `desktop-app/src/login.html`

---

Good luck! 🚀
