-- Migration to add known and suspected predator columns to the citizens table
ALTER TABLE citizens
ADD COLUMN griefer_known BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN griefer_suspected BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN murder_hobo_known BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN murder_hobo_suspected BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN pirate_known BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN pirate_suspected BOOLEAN DEFAULT FALSE NOT NULL;

-- Update the updated_at column to automatically update on row modification
ALTER TABLE citizens
ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP,
ALTER COLUMN updated_at SET DATA TYPE TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
