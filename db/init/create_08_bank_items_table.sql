-- Bank Items Table
-- Tracks item deposits and withdrawals from the Star Citizen Wiki API
-- Stores full metadata for accurate item tracking

CREATE TABLE IF NOT EXISTS bank_items (
    id SERIAL PRIMARY KEY,

    -- Item identification from Star Citizen Wiki API
    item_uuid TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    item_sub_type TEXT,
    item_category TEXT NOT NULL CHECK (item_category IN ('armor', 'weapons', 'vehicle-items', 'other')),
    manufacturer_name TEXT,
    manufacturer_code TEXT,

    -- Component-specific metadata (vehicle items)
    size TEXT,
    grade TEXT,
    class TEXT,

    -- Transaction details
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    description TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'withdrawn')) DEFAULT 'pending',
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('deposit', 'withdrawal')),

    -- User who submitted the request
    submitted_by_discord_id BIGINT NOT NULL,
    submitted_by_discord_name TEXT NOT NULL,

    -- User who processed the request (admin approval/rejection)
    processed_by_discord_id BIGINT,
    processed_by_discord_name TEXT,
    processed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    FOREIGN KEY (submitted_by_discord_id) REFERENCES citizens(discord_user_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bank_items_status ON bank_items (status);
CREATE INDEX IF NOT EXISTS idx_bank_items_submitted_by ON bank_items (submitted_by_discord_id);
CREATE INDEX IF NOT EXISTS idx_bank_items_item_name ON bank_items (item_name);
CREATE INDEX IF NOT EXISTS idx_bank_items_item_uuid ON bank_items (item_uuid);
CREATE INDEX IF NOT EXISTS idx_bank_items_category ON bank_items (item_category);
CREATE INDEX IF NOT EXISTS idx_bank_items_created_at ON bank_items (created_at);
CREATE INDEX IF NOT EXISTS idx_bank_items_deleted_at ON bank_items (deleted_at) WHERE deleted_at IS NULL;
