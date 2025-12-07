-- Migration: Fix integer overflow for large material quantities
-- Date: 2025-12-07
-- Issue: Manufacturing high-quantity items (e.g., Titanium Chromide) caused integer overflow
--        when calculating recursive material requirements
-- Solution: Change quantity and runs columns from INTEGER to BIGINT

-- Change quantity and runs to BIGINT to support large material calculations
ALTER TABLE shopping_list_items
  ALTER COLUMN quantity TYPE BIGINT,
  ALTER COLUMN runs TYPE BIGINT;

-- Note: PostgreSQL max values:
-- INTEGER: 2,147,483,647 (2.1 billion)
-- BIGINT: 9,223,372,036,854,775,807 (9.2 quintillion)
