import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

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
        conn = self.get_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            conn.commit()
            return cursor.rowcount
    
    def close_connection(self):
        if self.connection and not self.connection.closed:
            self.connection.close()


supabase_client = SupabaseClient()