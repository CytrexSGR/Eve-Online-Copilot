-- copilot_server/db/migrations/004_agent_runtime_core.sql

-- Agent Sessions (persistent audit trail)
CREATE TABLE IF NOT EXISTS agent_sessions (
    id VARCHAR(255) PRIMARY KEY,
    character_id INTEGER NOT NULL,
    autonomy_level INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_activity TIMESTAMP NOT NULL DEFAULT NOW(),
    archived BOOLEAN DEFAULT FALSE,
    context JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_agent_sessions_character_id ON agent_sessions(character_id);
CREATE INDEX idx_agent_sessions_status ON agent_sessions(status);
CREATE INDEX idx_agent_sessions_last_activity ON agent_sessions(last_activity);

-- Conversation Messages
CREATE TABLE IF NOT EXISTS agent_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_messages_session_id ON agent_messages(session_id);

-- Grant permissions
GRANT ALL ON agent_sessions TO eve;
GRANT ALL ON agent_messages TO eve;
GRANT USAGE, SELECT ON SEQUENCE agent_messages_id_seq TO eve;
