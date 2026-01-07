-- Migration 005: Add milestone alert tracking to battles
-- Enables smart milestone-based Telegram notifications
-- Author: Claude Sonnet 4.5
-- Date: 2026-01-07

-- Add milestone tracking columns
ALTER TABLE battles
ADD COLUMN IF NOT EXISTS last_milestone_notified INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS telegram_message_id BIGINT,
ADD COLUMN IF NOT EXISTS initial_alert_sent BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN battles.last_milestone_notified IS 'Last kill milestone that triggered an alert (0, 10, 25, 50, 100)';
COMMENT ON COLUMN battles.telegram_message_id IS 'Telegram message ID for editing existing alerts';
COMMENT ON COLUMN battles.initial_alert_sent IS 'Whether initial "New Battle" alert was sent';

-- Index for finding battles that need milestone alerts
CREATE INDEX IF NOT EXISTS idx_battles_milestone_pending
ON battles(status, total_kills, last_milestone_notified)
WHERE status = 'active';
