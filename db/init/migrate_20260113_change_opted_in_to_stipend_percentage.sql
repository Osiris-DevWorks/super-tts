-- Migrate distribution_opt_in table from opted_in boolean to stipend_percentage integer
-- opted_in = TRUE becomes stipend_percentage = 100
-- opted_in = FALSE becomes stipend_percentage = 0
-- This migration is idempotent: only runs if opted_in column exists

DO $$
BEGIN
    -- Check if opted_in column exists (old schema)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'distribution_opt_in' AND column_name = 'opted_in'
    ) THEN
        -- Add stipend_percentage column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'distribution_opt_in' AND column_name = 'stipend_percentage'
        ) THEN
            ALTER TABLE distribution_opt_in
            ADD COLUMN stipend_percentage INTEGER DEFAULT 100 CHECK (stipend_percentage >= 0 AND stipend_percentage <= 100);
        END IF;

        -- Migrate existing data from opted_in to stipend_percentage
        UPDATE distribution_opt_in
        SET stipend_percentage = CASE
            WHEN opted_in = TRUE THEN 100
            WHEN opted_in = FALSE THEN 0
            ELSE 100
        END
        WHERE stipend_percentage = 100;  -- Only update if still at default

        -- Drop the old opted_in column
        ALTER TABLE distribution_opt_in
        DROP COLUMN opted_in;
    END IF;
END $$;
