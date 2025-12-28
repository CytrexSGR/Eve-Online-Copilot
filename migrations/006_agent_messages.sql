-- Agent messages table for chat persistence
-- Drop existing table if it exists (with different schema)
DROP TABLE IF EXISTS agent_messages CASCADE;

CREATE TABLE IF NOT EXISTS agent_messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    content_blocks JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    token_usage JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_messages_session ON agent_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_created ON agent_messages(created_at DESC);

-- Add message count to agent_sessions for quick lookup
ALTER TABLE agent_sessions
ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 0;
