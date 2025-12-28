-- Migration 006: Agent Events Table
-- Purpose: Store event audit trail for agent runtime

CREATE TABLE IF NOT EXISTS agent_events (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    plan_id VARCHAR(255) REFERENCES agent_plans(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_events_session_id ON agent_events(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_plan_id ON agent_events(plan_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_event_type ON agent_events(event_type);
CREATE INDEX IF NOT EXISTS idx_agent_events_timestamp ON agent_events(timestamp);

COMMENT ON TABLE agent_events IS 'Event audit trail for agent runtime debugging and monitoring';
COMMENT ON COLUMN agent_events.event_type IS 'Event type: plan_proposed, tool_call_started, etc.';
COMMENT ON COLUMN agent_events.payload IS 'JSON: event-specific data';

GRANT ALL ON agent_events TO eve;
GRANT ALL ON SEQUENCE agent_events_id_seq TO eve;
