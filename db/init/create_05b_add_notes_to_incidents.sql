-- Add notes column to incidents table
ALTER TABLE incidents
ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT NULL;
