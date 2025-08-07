-- Add magic link authentication columns and remove password-based auth
ALTER TABLE users ADD COLUMN IF NOT EXISTS magic_link_token VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS magic_link_expires_at TIMESTAMP WITH TIME ZONE;

-- Remove password_hash column since we're going passwordless
ALTER TABLE users DROP COLUMN IF EXISTS password_hash;

-- Create index for magic link token lookups
CREATE INDEX IF NOT EXISTS idx_users_magic_link_token ON users(magic_link_token) WHERE magic_link_token IS NOT NULL;

-- Create index for magic link expiry cleanup
CREATE INDEX IF NOT EXISTS idx_users_magic_link_expires ON users(magic_link_expires_at) WHERE magic_link_expires_at IS NOT NULL;