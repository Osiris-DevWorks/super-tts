-- Allow weight 0 for manual-only TWIRK tips
-- This migration updates the constraint to allow 0-10 weight range (was 1-10)
-- Weight 0 tips are for testing, special announcements, or tips to exclude from rotation

DO $$
BEGIN
    -- Check if twirk_tips table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'twirk_tips'
    ) THEN
        -- Drop the old constraint if it exists
        ALTER TABLE twirk_tips
        DROP CONSTRAINT IF EXISTS twirk_tips_tip_weight_check;

        -- Add the new constraint that allows 0-10
        ALTER TABLE twirk_tips
        ADD CONSTRAINT twirk_tips_tip_weight_check CHECK (tip_weight >= 0 AND tip_weight <= 10);
    END IF;
END $$;
