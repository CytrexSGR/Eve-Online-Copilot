-- Migration 005: Agent Plans Table
-- Purpose: Store execution plans for multi-tool workflows

CREATE TABLE IF NOT EXISTS agent_plans (
    id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    plan_data JSONB NOT NULL,
    status VARCHAR(50) NOT NULL,
    auto_executing BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMP,
    executed_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_agent_plans_session_id ON agent_plans(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_plans_status ON agent_plans(status);

COMMENT ON TABLE agent_plans IS 'Stores execution plans for replay, audit, and approval workflow';
COMMENT ON COLUMN agent_plans.plan_data IS 'JSON: {steps: [{tool, arguments, risk_level}], max_risk_level}';
COMMENT ON COLUMN agent_plans.status IS 'proposed, approved, rejected, executing, completed, failed';

-- Grant permissions
GRANT ALL ON agent_plans TO eve;
