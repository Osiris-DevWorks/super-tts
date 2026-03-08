-- Track who recommended each award
-- Use IF NOT EXISTS to make migration idempotent
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'awards_assigned' AND column_name = 'recommended_by'
    ) THEN
        ALTER TABLE awards_assigned ADD COLUMN recommended_by BIGINT DEFAULT NULL;
    END IF;
END $$;

-- Create index if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_awards_recommended_by ON awards_assigned(recommended_by) WHERE recommended_by IS NOT NULL;
