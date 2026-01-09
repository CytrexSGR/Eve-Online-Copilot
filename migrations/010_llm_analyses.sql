-- Migration: LLM Analyses Storage
-- Persistent storage for AI-generated strategic analyses

CREATE TABLE IF NOT EXISTS llm_analyses (
    id SERIAL PRIMARY KEY,
    analysis_type VARCHAR(50) NOT NULL DEFAULT 'alliance_wars',
    summary TEXT NOT NULL,
    insights JSONB DEFAULT '[]'::jsonb,
    trends JSONB DEFAULT '[]'::jsonb,
    metrics JSONB DEFAULT '{}'::jsonb,
    model VARCHAR(50) DEFAULT 'gpt-5-mini',
    tokens_used INTEGER DEFAULT 0,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_llm_analyses_type_time ON llm_analyses(analysis_type, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_analyses_generated_at ON llm_analyses(generated_at DESC);

-- Comment
COMMENT ON TABLE llm_analyses IS 'Stores AI-generated strategic analyses for historical tracking';
COMMENT ON COLUMN llm_analyses.analysis_type IS 'Type of analysis (alliance_wars, battle_report, etc.)';
COMMENT ON COLUMN llm_analyses.metrics IS 'Key metrics snapshot at time of analysis (kills, isk, efficiency)';
COMMENT ON COLUMN llm_analyses.trends IS 'Trend observations compared to previous analyses';
