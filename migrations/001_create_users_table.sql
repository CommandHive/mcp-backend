-- Create users table with wallet_address as primary key
CREATE TABLE IF NOT EXISTS users (
    wallet_address VARCHAR(42) PRIMARY KEY,  -- Ethereum addresses are 42 characters (0x + 40 hex chars)
    email VARCHAR(255) UNIQUE,
    username VARCHAR(50) UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    github_id VARCHAR(255),
    google_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    subscription_tier VARCHAR(20) DEFAULT 'free',
    nonce VARCHAR(32),  -- For wallet authentication nonce
    nonce_expires_at TIMESTAMP WITH TIME ZONE
);



-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_github_id ON users(github_id);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_subscription_tier ON users(subscription_tier);
CREATE INDEX IF NOT EXISTS idx_users_nonce_expires_at ON users(nonce_expires_at);

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE users IS 'User accounts with wallet-based authentication';
COMMENT ON COLUMN users.wallet_address IS 'Ethereum wallet address (primary key)';
COMMENT ON COLUMN users.nonce IS 'Temporary nonce for wallet signature verification';
COMMENT ON COLUMN users.nonce_expires_at IS 'Expiration time for the nonce';
COMMENT ON COLUMN users.subscription_tier IS 'User subscription level (free, pro, enterprise)';



```
      Column       |           Type           | Collation | Nullable |          Default          | Storage  | Compression | Stats target |                    Description
-------------------+--------------------------+-----------+----------+---------------------------+----------+-------------+--------------+---------------------------------------------------
 id                | uuid                     |           | not null | gen_random_uuid()         | plain    |             |              |
 email             | character varying(255)   |           | not null |                           | extended |             |              |
 username          | character varying(100)   |           | not null |                           | extended |             |              |
 display_name      | character varying(100)   |           | not null |                           | extended |             |              |
 avatar_url        | text                     |           |          |                           | extended |             |              |
 github_id         | character varying(100)   |           |          |                           | extended |             |              |
 google_id         | character varying(100)   |           |          |                           | extended |             |              |
 created_at        | timestamp with time zone |           |          | CURRENT_TIMESTAMP         | plain    |             |              |
 updated_at        | timestamp with time zone |           |          | CURRENT_TIMESTAMP         | plain    |             |              |
 is_active         | boolean                  |           |          | true                      | plain    |             |              |
 subscription_tier | character varying(50)    |           |          | 'free'::character varying | extended |             |              |
 nonce             | character varying(32)    |           |          |                           | extended |             |              | Temporary nonce for wallet signature verification
 nonce_expires_at  | timestamp with time zone |           |          |                           | plain    |             |              | Expiration time for the nonce
Indexes:
    "users_pkey" PRIMARY KEY, btree (id)
    "idx_users_nonce_expires_at" btree (nonce_expires_at)
    "users_email_key" UNIQUE CONSTRAINT, btree (email)
    "users_username_key" UNIQUE CONSTRAINT, btree (username)
Referenced by:
    TABLE "chat_sessions" CONSTRAINT "chat_sessions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    TABLE "server_collections" CONSTRAINT "server_collections_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    TABLE "server_reviews" CONSTRAINT "server_reviews_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    TABLE "server_stars" CONSTRAINT "server_stars_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    TABLE "server_versions" CONSTRAINT "server_versions_created_by_fkey" FOREIGN KEY (created_by) REFERENCES users(id)
    TABLE "servers" CONSTRAINT "servers_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
Triggers:
    update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
Access method: heap
```