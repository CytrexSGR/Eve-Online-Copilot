-- Stored Reports Table
-- Reports are generated every 6 hours by cron and stored here
-- API reads directly from this table (no cache expiry issues)

CREATE TABLE IF NOT EXISTS stored_reports (
    report_type VARCHAR(50) PRIMARY KEY,
    report_data JSONB NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    generation_time_seconds FLOAT,
    version INTEGER DEFAULT 1
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_stored_reports_generated_at ON stored_reports(generated_at);

-- Comments
COMMENT ON TABLE stored_reports IS 'Pre-generated intelligence reports, updated every 6 hours by cron';
COMMENT ON COLUMN stored_reports.report_type IS 'Report identifier: pilot_intelligence, war_profiteering, alliance_wars, trade_routes, war_economy, strategic_briefing, alliance_wars_analysis, war_economy_analysis';
COMMENT ON COLUMN stored_reports.report_data IS 'Full report data as JSON';
COMMENT ON COLUMN stored_reports.generated_at IS 'When this report was generated';
COMMENT ON COLUMN stored_reports.generation_time_seconds IS 'How long it took to generate';
