-- Migration: Add missing columns for bounty hostile checks to bounty_submissions table
-- Adds support for predator tracking, RSI dossier scraping, and hostile org checking

DO $$ BEGIN
    -- Add target_is_predator column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bounty_submissions' AND column_name = 'target_is_predator'
    ) THEN
        ALTER TABLE bounty_submissions ADD COLUMN target_is_predator BOOLEAN;
    END IF;

    -- Add rsi_org_affiliation column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bounty_submissions' AND column_name = 'rsi_org_affiliation'
    ) THEN
        ALTER TABLE bounty_submissions ADD COLUMN rsi_org_affiliation VARCHAR(255);
    END IF;

    -- Add rsi_org_is_known_hostile column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bounty_submissions' AND column_name = 'rsi_org_is_known_hostile'
    ) THEN
        ALTER TABLE bounty_submissions ADD COLUMN rsi_org_is_known_hostile BOOLEAN;
    END IF;
END $$;
