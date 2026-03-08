CREATE TABLE IF NOT EXISTS awards_assigned (
    id SERIAL PRIMARY KEY,
    discord_user_id BIGINT NOT NULL,
    award_type TEXT NOT NULL,
    reason TEXT DEFAULT NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (discord_user_id) REFERENCES citizens(discord_user_id) ON DELETE CASCADE,
    FOREIGN KEY (award_type) REFERENCES award_types(award_type) ON DELETE CASCADE
);
