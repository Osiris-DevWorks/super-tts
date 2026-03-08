-- Migration to add known and suspected predator columns to the citizens table
ALTER TABLE citizens
ADD COLUMN gmt INTEGER DEFAULT NULL,
ADD COLUMN other_rsi_orgs TEXT[] DEFAULT '{}';
