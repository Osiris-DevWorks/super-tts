-- Add foreign key constraints and indexes for incident organization tracking
-- Ensures data integrity by linking incidents to actual organizations in the database
-- Also adds indexes for query performance

-- Add foreign key constraint for victim_org_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_incidents_victim_org'
    ) THEN
        ALTER TABLE incidents
        ADD CONSTRAINT fk_incidents_victim_org
          FOREIGN KEY (victim_org_id) REFERENCES organizations(rsi_org_id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add foreign key constraint for predator_org_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_incidents_predator_org'
    ) THEN
        ALTER TABLE incidents
        ADD CONSTRAINT fk_incidents_predator_org
          FOREIGN KEY (predator_org_id) REFERENCES organizations(rsi_org_id) ON DELETE SET NULL;
    END IF;
END $$;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_incidents_victim_org_id ON incidents(victim_org_id);
CREATE INDEX IF NOT EXISTS idx_incidents_predator_org_id ON incidents(predator_org_id);
CREATE INDEX IF NOT EXISTS idx_incidents_incident_date ON incidents(incident_date);
CREATE INDEX IF NOT EXISTS idx_incidents_approved_at ON incidents(approved_at);
