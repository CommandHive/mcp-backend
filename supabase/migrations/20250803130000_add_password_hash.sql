-- Add password_hash column to users table for email authentication
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);

-- Create index for email lookups with password
CREATE INDEX idx_users_email_password ON users(email) WHERE password_hash IS NOT NULL;