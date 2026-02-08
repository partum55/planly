# Agent 1 Prompt: Backend Webserver (Core AI Agent)

## Project Overview

You are building **Planly** - a multi-platform AI agent system for a hackathon. The system has:
1. **Centralized Webserver (YOUR RESPONSIBILITY)** - Python FastAPI backend with core AI agent
2. **Telegram Bot Client** - (Other agent) Forwards messages to your webserver
3. **Desktop Electron App** - (Other agent) Takes screenshots, sends to your webserver

Your job is to build the **intelligent backend** that processes conversations, extracts intent, and executes actions via tools.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Clients (Other Agent Builds These)                          │
│                                                               │
│  • Telegram Bot → sends messages to your webserver           │
│  • Desktop App → sends screenshots (OCR'd) to your webserver │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP/JSON
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  YOUR WEBSERVER (FastAPI on localhost:8000)                  │
│                                                               │
│  API Endpoints:                                               │
│  • POST /auth/register, /login, /refresh                     │
│  • POST /agent/process (main endpoint - process conversation)│
│  • POST /agent/confirm-actions (execute confirmed actions)   │
│  • POST /telegram/webhook (receive Telegram messages)        │
│  • GET  /conversations, /calendar/events, /user/profile      │
│                                                               │
│  Core Components:                                             │
│  • Agent (ORPLAR loop: Observe→Reason→Plan→Act→Respond)     │
│  • Reasoning Engine (Ollama LLM integration)                  │
│  • Context Manager (rolling 1-hour window)                    │
│  • Tool System (Calendar, Restaurant, Cinema)                 │
│  • Authentication (OAuth, JWT)                                │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  External Services                                            │
│  • Supabase (PostgreSQL database)                             │
│  • Ollama (LLM for reasoning)                                 │
│  • Google Calendar API                                        │
│  • Yelp/Google Places API                                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Your Responsibilities

### 1. Database (Supabase/PostgreSQL)

Create schema with these tables:

```sql
-- Users and authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    telegram_id BIGINT UNIQUE,
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    preferences JSONB DEFAULT '{}'
);

CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token TEXT UNIQUE NOT NULL,
    client_type TEXT NOT NULL,  -- 'desktop', 'telegram'
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations (Telegram groups + desktop sessions)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    conversation_type TEXT NOT NULL,  -- 'telegram_group', 'desktop_screenshot'
    telegram_group_id BIGINT UNIQUE,
    telegram_group_title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages (rolling 1-hour window)
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id BIGINT,
    username TEXT,
    text TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,  -- 'telegram', 'desktop_ocr'
    is_bot_mention BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_messages_conversation_timestamp ON messages(conversation_id, timestamp DESC);

-- Cleanup old messages
CREATE OR REPLACE FUNCTION cleanup_old_messages() RETURNS void AS $$
BEGIN
    DELETE FROM messages WHERE timestamp < NOW() - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;

-- Calendar events
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    created_by_user_id UUID NOT NULL REFERENCES users(id),
    calendar_event_id TEXT,
    activity_type TEXT NOT NULL,
    activity_name TEXT,
    participants JSONB NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log
CREATE TABLE agent_actions (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    user_id UUID REFERENCES users(id),
    trigger_source TEXT NOT NULL,
    intent_data JSONB NOT NULL,
    tool_calls JSONB NOT NULL,
    response_text TEXT,
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**File:** `server/database/supabase_schema.sql`

### 2. Core AI Agent (ORPLAR Loop)

**File:** `server/core/agent.py`

```python
class TelegramAgent:
    """
    Main agent orchestrator implementing:
    Observe → Reason → Plan → Act → Respond
    """

    async def process_mention(self, group_id: int, message_id: int) -> str:
        """Main entry point when bot is mentioned"""

        # 1. OBSERVE: Get rolling 1-hour conversation context
        context = await self.context_manager.get_context(group_id)

        # 2. REASON: Extract intent from conversation
        intent = await self.reasoning_engine.extract_intent(context)

        # Check if clarification needed
        if intent.clarification_needed:
            return intent.clarification_needed

        # 3. PLAN: Determine which tools to use
        action_plan = await self.reasoning_engine.create_action_plan(intent)

        # 4. ACT: Execute tools in sequence
        results = await self.execute_plan(action_plan)

        # 5. RESPOND: Format response
        response = await self.reasoning_engine.compose_response(intent, results)

        return response
```

**Intent Model:** `server/models/intent.py`
```python
class Intent(BaseModel):
    activity_type: str  # restaurant, cinema, meeting
    participants: List[TelegramUser]
    datetime: Optional[datetime]
    location: Optional[str]
    requirements: Dict[str, Any]  # cuisine, price_range, etc.
    confidence: float
    clarification_needed: Optional[str]
```

### 3. Reasoning Engine (LLM Integration)

**File:** `server/integrations/ollama/client.py`

```python
class OllamaClient:
    def __init__(self, endpoint: str, model: str):
        self.endpoint = endpoint  # http://localhost:11434
        self.model = model  # llama3.1:8b

    async def generate_structured(self, prompt: str, schema: BaseModel):
        """Generate response with JSON schema validation"""
        # Call Ollama API, parse JSON, validate with Pydantic
```

**File:** `server/core/reasoning_engine.py`

```python
class ReasoningEngine:
    async def extract_intent(self, context: dict) -> Intent:
        """Extract structured intent using LLM"""
        prompt = f"""
        Extract intent from conversation:
        {context['messages']}

        Return JSON:
        {{
            "activity_type": "restaurant|cinema|meeting",
            "participants": [...],
            "datetime": "ISO8601",
            "location": "...",
            "confidence": 0.0-1.0
        }}
        """
        return await self.ollama.generate_structured(prompt, Intent)

    async def create_action_plan(self, intent: Intent) -> ActionPlan:
        """Determine which tools to invoke"""
        # Use LLM to plan tool sequence
```

### 4. Tool System

**File:** `server/tools/base.py`

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        pass

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, tool: BaseTool):
        self.tools[tool.schema.name] = tool
```

**File:** `server/tools/calendar_tool.py`

```python
class CalendarTool(BaseTool):
    async def execute(self, title, datetime, duration_minutes=120, **kwargs):
        """Create Google Calendar event"""
        # Use service account to create event
        # Return event_id and event_link
```

**File:** `server/tools/restaurant_tool.py`

```python
class RestaurantSearchTool(BaseTool):
    async def execute(self, location, cuisine=None, price_range=None):
        """Search restaurants via Yelp or Google Places"""
        # Return list of restaurants with details
```

### 5. API Routes (FastAPI)

**File:** `server/api/app.py`

```python
from fastapi import FastAPI
from api.routes import auth, agent, telegram, conversations, calendar, user

app = FastAPI(title="Planly API")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
# ... other routes
```

**File:** `server/api/routes/agent.py`

```python
@router.post("/process")
async def process_conversation(
    request: AgentProcessRequest,
    user: User = Depends(get_current_user)
):
    """
    Main endpoint for processing conversations

    Request:
    {
        "source": "desktop_screenshot" | "telegram",
        "context": {
            "messages": [
                {"username": "Alice", "text": "...", "timestamp": "..."}
            ]
        }
    }

    Response:
    {
        "conversation_id": "uuid",
        "intent": {...},
        "proposed_actions": [
            {"action_id": "uuid", "tool": "...", "description": "..."}
        ]
    }
    """
    # 1. Store messages in database
    # 2. Call agent.process_mention()
    # 3. Return intent and proposed actions

@router.post("/confirm-actions")
async def confirm_actions(
    request: ConfirmActionsRequest,
    user: User = Depends(get_current_user)
):
    """
    Execute confirmed actions (for desktop app)

    Request:
    {
        "conversation_id": "uuid",
        "action_ids": ["uuid1", "uuid2"]
    }

    Response:
    {
        "results": [
            {"action_id": "uuid1", "success": true, "result": {...}}
        ]
    }
    """
    # Execute tools and return results
```

**File:** `server/api/routes/telegram.py`

```python
@router.post("/webhook")
async def telegram_webhook(request: TelegramWebhookRequest):
    """
    Receive messages from Telegram bot client

    Request:
    {
        "group_id": 123456,
        "message_id": 789,
        "user_id": 111,
        "username": "alice",
        "text": "...",
        "timestamp": "...",
        "is_bot_mention": false
    }

    Response:
    {
        "response_text": "..." | null
    }
    """
    # 1. Store message in database
    # 2. If is_bot_mention: call agent.process_mention()
    # 3. Return response_text if available
```

**File:** `server/api/routes/auth.py`

```python
@router.post("/register")
async def register(request: RegisterRequest):
    """User registration"""
    # Hash password, create user, generate JWT

@router.post("/login")
async def login(request: LoginRequest):
    """User login"""
    # Verify password, generate access + refresh tokens

@router.post("/refresh")
async def refresh(request: RefreshRequest):
    """Refresh access token"""
    # Validate refresh token, issue new access token
```

### 6. Authentication

**File:** `server/services/auth_service.py`

```python
import bcrypt
import jwt

class AuthService:
    def register_user(self, email, password, full_name):
        """Create new user account"""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        # Save to database

    def verify_login(self, email, password):
        """Verify credentials and return user"""
        # Check password hash

    def generate_tokens(self, user_id):
        """Generate JWT access + refresh tokens"""
        access_token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, SECRET_KEY)
        # Generate refresh token
        return access_token, refresh_token
```

**File:** `server/api/middleware/auth_middleware.py`

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)):
    """Validate JWT and return user"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user = await user_repo.get_by_id(payload['user_id'])
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
```

---

## Environment Setup

**File:** `server/.env.example`

```bash
# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_service_role_key

# Ollama
OLLAMA_ENDPOINT=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Google Calendar
GOOGLE_CALENDAR_ID=your_calendar@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_FILE=./integrations/google_calendar/service_account.json

# Yelp/Places
YELP_API_KEY=your_yelp_key
GOOGLE_PLACES_API_KEY=your_places_key

# Auth
JWT_SECRET_KEY=your_random_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Server
HOST=0.0.0.0
PORT=8000
```

---

## Dependencies

**File:** `server/requirements.txt`

```txt
# FastAPI
fastapi==0.109.0
uvicorn==0.27.0
pydantic==2.5.3

# Database
supabase==2.3.0
psycopg2-binary==2.9.9

# Authentication
pyjwt==2.8.0
bcrypt==4.1.2

# LLM
httpx==0.26.0

# Google Calendar
google-auth==2.26.2
google-api-python-client==2.111.0

# External APIs
yelp-fusion==1.0.1
googlemaps==4.10.0

# Utilities
python-dotenv==1.0.0
dateparser==1.2.0
tenacity==8.2.3

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```

---

## Step-by-Step Implementation

### Step 1: Project Setup
```bash
mkdir -p server/api/routes server/core server/tools server/database/repositories server/integrations/ollama server/services server/models
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Database
1. Create Supabase project at supabase.com
2. Copy `supabase_schema.sql` to Supabase SQL Editor and execute
3. Get project URL and service role key → `.env`

### Step 3: Core Agent
Implement in this order:
1. `models/intent.py`, `models/message.py`, `models/action.py`
2. `database/repositories/user_repo.py`, `conversation_repo.py`, `event_repo.py`
3. `integrations/ollama/client.py`
4. `core/context_manager.py`
5. `core/reasoning_engine.py`
6. `core/agent.py`

### Step 4: Tools
1. `tools/base.py` - Base classes
2. `tools/calendar_tool.py` - Google Calendar
3. `tools/restaurant_tool.py` - Yelp/Places
4. `tools/cinema_tool.py` - Mock data

### Step 5: Authentication
1. `services/auth_service.py`
2. `api/middleware/auth_middleware.py`
3. `api/routes/auth.py`

### Step 6: API Routes
1. `api/app.py` - FastAPI app
2. `api/routes/agent.py` - Main endpoints
3. `api/routes/telegram.py` - Telegram webhook
4. `api/routes/conversations.py`, `calendar.py`, `user.py`

### Step 7: Entry Point
```python
# server/main.py
import uvicorn
from api.app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Testing

### Test with Postman/curl

**1. Register user:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass", "full_name": "Test User"}'
```

**2. Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass"}'
# Save the access_token
```

**3. Test agent processing:**
```bash
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "source": "desktop_screenshot",
    "context": {
      "messages": [
        {"username": "Alice", "text": "Lets get dinner tomorrow at 7pm", "timestamp": "2026-02-08T18:00:00Z"},
        {"username": "Bob", "text": "Im in!", "timestamp": "2026-02-08T18:01:00Z"}
      ]
    }
  }'
```

**4. Confirm actions:**
```bash
curl -X POST http://localhost:8000/agent/confirm-actions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "conversation_id": "<uuid_from_previous_response>",
    "action_ids": ["<action_id_1>", "<action_id_2>"]
  }'
```

---

## Success Criteria

✅ Webserver running on http://localhost:8000
✅ All API endpoints functional (test with Postman)
✅ Agent can extract intent from conversation messages
✅ Tools can execute (create calendar events, search restaurants)
✅ Authentication working (register, login, JWT validation)
✅ Database storing conversations, messages, events
✅ Other agent can integrate their clients with your API

---

## Tips

1. **Start simple:** Get basic API working first, then add LLM reasoning
2. **Mock LLM initially:** Return hardcoded intent to unblock API development
3. **Test frequently:** Use Postman to test each endpoint as you build
4. **Log everything:** Add logging to debug issues
5. **Share API docs:** Generate FastAPI docs at http://localhost:8000/docs

---

## Your Next Steps

1. Set up project structure
2. Create database schema in Supabase
3. Implement authentication system
4. Build basic API endpoints (can return mocked responses)
5. Share API documentation with other agent
6. Implement core agent logic
7. Integrate Ollama for reasoning
8. Build tool system
9. Test end-to-end with Postman

Good luck! 🚀
