import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment-specific .env file
environment = os.getenv("ENVIRONMENT", "prod")
env_file = f".env.{environment}"

# Try to load the environment-specific file, fallback to .env
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv()


class SupabaseClient:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL must be set in environment variables")
        
        self.connection = None
    
    def get_connection(self):
        if not self.connection or self.connection.closed:
            self.connection = psycopg2.connect(
                self.database_url,
                cursor_factory=RealDictCursor
            )
        return self.connection
    
    def execute_query(self, query: str, params=None):
        print("Connecting to:", self.database_url)
        print(f"[DEBUG] Executing query: {query}")
        print(f"[DEBUG] With params: {params}")
        conn = self.get_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT') or 'RETURNING' in query.upper():
                return cursor.fetchall()
            conn.commit()
            return cursor.rowcount
    
    def close_connection(self):
        if self.connection and not self.connection.closed:
            self.connection.close()


supabase_client = SupabaseClient()