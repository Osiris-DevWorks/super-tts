-- Add soft-delete support to awards_assigned table
-- This allows award types to be soft-deleted while keeping their assigned awards visible

-- Add missing columns for soft-delete and status tracking
ALTER TABLE awards_assigned
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'awarded' CHECK (status IN ('awarded', 'recommended', 'declined', 'revoked')),
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

-- Create index on status and deleted_at for efficient filtering
CREATE INDEX IF NOT EXISTS idx_awards_assigned_status ON awards_assigned(status);
CREATE INDEX IF NOT EXISTS idx_awards_assigned_deleted_at ON awards_assigned(deleted_at);
CREATE INDEX IF NOT EXISTS idx_awards_assigned_award_type ON awards_assigned(award_type);

-- Drop the old cascade delete foreign key constraint
ALTER TABLE awards_assigned
DROP CONSTRAINT IF EXISTS awards_assigned_award_type_fkey;

-- Recreate the foreign key with RESTRICT to prevent deletion of award types with assigned awards
ALTER TABLE awards_assigned
ADD CONSTRAINT awards_assigned_award_type_fkey
  FOREIGN KEY (award_type) REFERENCES award_types(award_type) ON DELETE RESTRICT;
