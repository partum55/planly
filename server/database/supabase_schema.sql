-- Planly Database Schema
-- PostgreSQL / Supabase

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users and authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    telegram_id BIGINT UNIQUE,
    telegram_username TEXT,
    full_name TEXT,
    avatar_url TEXT,
    oauth_provider TEXT,  -- 'google', 'telegram', 'local'
    oauth_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    preferences JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id) WHERE telegram_id IS NOT NULL;
CREATE INDEX idx_users_email ON users(email);

-- User sessions for JWT management
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token TEXT UNIQUE NOT NULL,
    device_info JSONB,
    client_type TEXT NOT NULL,  -- 'desktop', 'telegram', 'web'
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(refresh_token);

-- Conversations (Telegram groups + desktop sessions)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    conversation_type TEXT NOT NULL,  -- 'telegram_group', 'desktop_screenshot'
    telegram_group_id BIGINT,
    telegram_group_title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    settings JSONB DEFAULT '{}'::jsonb,
    UNIQUE(telegram_group_id)
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_telegram_group ON conversations(telegram_group_id)
    WHERE telegram_group_id IS NOT NULL;

-- Messages (rolling 1-hour window)
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    message_id BIGINT,
    user_id BIGINT,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    text TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,  -- 'telegram', 'desktop_ocr'
    is_bot_mention BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(conversation_id, message_id)
);

CREATE INDEX idx_messages_conversation_timestamp
    ON messages(conversation_id, timestamp DESC);
CREATE INDEX idx_messages_bot_mention
    ON messages(conversation_id, is_bot_mention)
    WHERE is_bot_mention = TRUE;

-- Cleanup function for messages older than 1 hour
CREATE OR REPLACE FUNCTION cleanup_old_messages()
RETURNS void AS $$
BEGIN
    DELETE FROM messages WHERE timestamp < NOW() - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;

-- Calendar events
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    created_by_user_id UUID NOT NULL REFERENCES users(id),
    calendar_event_id TEXT,
    activity_type TEXT NOT NULL,  -- restaurant, cinema, meeting, etc.
    activity_name TEXT,
    activity_details JSONB,
    participants JSONB NOT NULL,  -- Array of participant info
    event_time TIMESTAMPTZ NOT NULL,
    location TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by_message_id BIGINT,
    status TEXT DEFAULT 'active',  -- active, cancelled, completed
    confirmed BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_events_conversation_time ON events(conversation_id, event_time DESC);
CREATE INDEX idx_events_user_id ON events(created_by_user_id);

-- Agent actions audit log
CREATE TABLE agent_actions (
    id BIGSERIAL PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    trigger_source TEXT NOT NULL,  -- 'telegram_mention', 'desktop_keybind'
    trigger_message_id BIGINT,
    action_type TEXT NOT NULL,
    intent_data JSONB NOT NULL,
    tool_calls JSONB NOT NULL,
    response_text TEXT,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_actions_conversation ON agent_actions(conversation_id, created_at DESC);
CREATE INDEX idx_agent_actions_user ON agent_actions(user_id, created_at DESC);

-- Desktop screenshots metadata (optional, for debugging)
CREATE TABLE desktop_screenshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    file_path TEXT,
    ocr_text TEXT,
    ocr_confidence FLOAT,
    window_title TEXT,
    app_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_screenshots_user_id ON desktop_screenshots(user_id, created_at DESC);

-- Comments
COMMENT ON TABLE users IS 'User accounts with OAuth support';
COMMENT ON TABLE user_sessions IS 'JWT session management';
COMMENT ON TABLE conversations IS 'Telegram groups and desktop screenshot sessions';
COMMENT ON TABLE messages IS 'Rolling 1-hour message window';
COMMENT ON TABLE events IS 'Created calendar events';
COMMENT ON TABLE agent_actions IS 'Audit log of all agent actions';

-- Action plan cache (replaces in-memory dict for multi-worker safety)
CREATE TABLE IF NOT EXISTS action_plan_cache (
    conversation_id TEXT PRIMARY KEY,
    intent_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    tool_calls JSONB NOT NULL DEFAULT '[]'::jsonb,
    idempotency_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_action_plan_cache_created ON action_plan_cache(created_at);

-- Auto-cleanup expired cache entries (older than 15 minutes)
CREATE OR REPLACE FUNCTION cleanup_expired_action_plans()
RETURNS void AS $$
BEGIN
    DELETE FROM action_plan_cache WHERE created_at < NOW() - INTERVAL '15 minutes';
END;
$$ LANGUAGE plpgsql;
