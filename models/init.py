import psycopg2
from services.supabase_client import supabase_client


def create_tables():
    """Create all PostgreSQL tables based on the defined models."""
    
    create_users_table = """
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
    """
    
    create_servers_table = """
    CREATE TABLE IF NOT EXISTS servers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        wallet_address VARCHAR(42) NOT NULL REFERENCES users(wallet_address) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        slug VARCHAR(255) UNIQUE NOT NULL,
        description TEXT,
        version VARCHAR(50) DEFAULT '1.0.0',
        status VARCHAR(50) DEFAULT 'inactive',
        visibility VARCHAR(50) DEFAULT 'private',
        source_code TEXT,
        package_json JSONB,
        environment_vars JSONB,
        container_id VARCHAR(255),
        deployment_url TEXT,
        health_check_url TEXT,
        last_deployed_at TIMESTAMP WITH TIME ZONE,
        total_requests INTEGER DEFAULT 0,
        last_accessed_at TIMESTAMP WITH TIME ZONE,
        tags TEXT[],
        category VARCHAR(100),
        is_featured BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_server_versions_table = """
    CREATE TABLE IF NOT EXISTS server_versions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
        version VARCHAR(50) NOT NULL,
        source_code TEXT,
        package_json JSONB,
        changelog TEXT,
        created_by VARCHAR(42) NOT NULL REFERENCES users(wallet_address),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_server_tools_table = """
    CREATE TABLE IF NOT EXISTS server_tools (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        schema JSONB,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_server_usage_logs_table = """
    CREATE TABLE IF NOT EXISTS server_usage_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
        tool_name VARCHAR(255),
        client_identifier VARCHAR(255),
        request_data JSONB,
        response_status INTEGER,
        response_time_ms INTEGER,
        error_message TEXT,
        ip_address INET,
        user_agent TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_server_collections_table = """
    CREATE TABLE IF NOT EXISTS server_collections (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        wallet_address VARCHAR(42) NOT NULL REFERENCES users(wallet_address) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        is_public BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_collection_servers_table = """
    CREATE TABLE IF NOT EXISTS collection_servers (
        collection_id UUID NOT NULL REFERENCES server_collections(id) ON DELETE CASCADE,
        server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
        added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (collection_id, server_id)
    );
    """
    
    create_server_stars_table = """
    CREATE TABLE IF NOT EXISTS server_stars (
        wallet_address VARCHAR(42) NOT NULL REFERENCES users(wallet_address) ON DELETE CASCADE,
        server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (wallet_address, server_id)
    );
    """
    
    create_server_reviews_table = """
    CREATE TABLE IF NOT EXISTS server_reviews (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
        wallet_address VARCHAR(42) NOT NULL REFERENCES users(wallet_address) ON DELETE CASCADE,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        comment TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(server_id, wallet_address)
    );
    """
    
    create_deployment_logs_table = """
    CREATE TABLE IF NOT EXISTS deployment_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
        version VARCHAR(50) NOT NULL,
        status VARCHAR(50) NOT NULL,
        build_logs TEXT,
        error_message TEXT,
        deployment_config JSONB,
        started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP WITH TIME ZONE
    );
    """
    
    create_chat_sessions_table = """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        wallet_address VARCHAR(42) NOT NULL REFERENCES users(wallet_address) ON DELETE CASCADE,
        server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
        title VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_chat_messages_table = """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_indexes = """
    CREATE INDEX IF NOT EXISTS idx_servers_wallet_address ON servers(wallet_address);
    CREATE INDEX IF NOT EXISTS idx_servers_slug ON servers(slug);
    CREATE INDEX IF NOT EXISTS idx_servers_status ON servers(status);
    CREATE INDEX IF NOT EXISTS idx_servers_visibility ON servers(visibility);
    CREATE INDEX IF NOT EXISTS idx_servers_category ON servers(category);
    CREATE INDEX IF NOT EXISTS idx_server_versions_server_id ON server_versions(server_id);
    CREATE INDEX IF NOT EXISTS idx_server_tools_server_id ON server_tools(server_id);
    CREATE INDEX IF NOT EXISTS idx_server_usage_logs_server_id ON server_usage_logs(server_id);
    CREATE INDEX IF NOT EXISTS idx_server_usage_logs_created_at ON server_usage_logs(created_at);
    CREATE INDEX IF NOT EXISTS idx_server_collections_wallet_address ON server_collections(wallet_address);
    CREATE INDEX IF NOT EXISTS idx_chat_sessions_wallet_address ON chat_sessions(wallet_address);
    CREATE INDEX IF NOT EXISTS idx_chat_sessions_server_id ON chat_sessions(server_id);
    CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
    """
    
    create_triggers = """
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    DROP TRIGGER IF EXISTS update_users_updated_at ON users;
    CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();

    DROP TRIGGER IF EXISTS update_servers_updated_at ON servers;
    CREATE TRIGGER update_servers_updated_at
        BEFORE UPDATE ON servers
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();

    DROP TRIGGER IF EXISTS update_server_reviews_updated_at ON server_reviews;
    CREATE TRIGGER update_server_reviews_updated_at
        BEFORE UPDATE ON server_reviews
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();

    DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON chat_sessions;
    CREATE TRIGGER update_chat_sessions_updated_at
        BEFORE UPDATE ON chat_sessions
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """
    
    tables = [
        create_users_table,
        create_servers_table,
        create_server_versions_table,
        create_server_tools_table,
        create_server_usage_logs_table,
        create_server_collections_table,
        create_collection_servers_table,
        create_server_stars_table,
        create_server_reviews_table,
        create_deployment_logs_table,
        create_chat_sessions_table,
        create_chat_messages_table,
        create_indexes,
        create_triggers
    ]
    
    try:
        for table_sql in tables:
            supabase_client.execute_query(table_sql)
        print("All tables created successfully!")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False


def drop_all_tables():
    """Drop all tables (use with caution)."""
    drop_tables_sql = """
    DROP TABLE IF EXISTS chat_messages CASCADE;
    DROP TABLE IF EXISTS chat_sessions CASCADE;
    DROP TABLE IF EXISTS deployment_logs CASCADE;
    DROP TABLE IF EXISTS server_reviews CASCADE;
    DROP TABLE IF EXISTS server_stars CASCADE;
    DROP TABLE IF EXISTS collection_servers CASCADE;
    DROP TABLE IF EXISTS server_collections CASCADE;
    DROP TABLE IF EXISTS server_usage_logs CASCADE;
    DROP TABLE IF EXISTS server_tools CASCADE;
    DROP TABLE IF EXISTS server_versions CASCADE;
    DROP TABLE IF EXISTS servers CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
    """
    
    try:
        supabase_client.execute_query(drop_tables_sql)
        print("All tables dropped successfully!")
        return True
    except Exception as e:
        print(f"Error dropping tables: {e}")
        return False


def check_tables_exist():
    """Check if all required tables exist in the database."""
    check_query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """
    
    try:
        result = supabase_client.execute_query(check_query)
        existing_tables = [row['table_name'] for row in result]
        
        required_tables = [
            'users', 'servers', 'server_versions', 'server_tools',
            'server_usage_logs', 'server_collections', 'collection_servers',
            'server_stars', 'server_reviews', 'deployment_logs',
            'chat_sessions', 'chat_messages'
        ]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        print(f"Existing tables: {existing_tables}")
        if missing_tables:
            print(f"Missing tables: {missing_tables}")
            return False
        else:
            print("All required tables exist!")
            return True
            
    except Exception as e:
        print(f"Error checking tables: {e}")
        return False


if __name__ == "__main__":
    print("Checking if tables exist...")
    if not check_tables_exist():
        print("Creating missing tables...")
        create_tables()
    else:
        print("Database is already initialized!")