-- Migration: Add promotion notification tracking
-- Tracks the last date a promotion notification was posted
-- Ensures notifications only post once per Friday

CREATE TABLE IF NOT EXISTS promotion_notifications (
    id SERIAL PRIMARY KEY,
    last_notification_date DATE NOT NULL,
    notification_count INT DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Initialize with a row (singleton pattern for tracking state) using UPSERT
-- This ensures the row exists and is updated on each migration run
INSERT INTO promotion_notifications (id, last_notification_date, notification_count)
VALUES (1, CURRENT_DATE - INTERVAL '8 days', 1)
ON CONFLICT (id) DO UPDATE
SET last_notification_date = EXCLUDED.last_notification_date,
    updated_at = CURRENT_TIMESTAMP;
