import json
import uuid
from typing import Optional, Dict, List, Any
from services.supabase_client import supabase_client


class ServerDatabaseService:
    """Database service for server operations"""
    
    @staticmethod
    def check_slug_exists(slug: str) -> bool:
        """Check if a server slug already exists"""
        query = "SELECT id FROM servers WHERE slug = %s"
        result = supabase_client.execute_query(query, (slug,))
        return bool(result)
    
    @staticmethod
    def generate_unique_slug(base_slug: str) -> str:
        """Generate a unique slug by appending numbers if needed"""
        slug = base_slug
        counter = 1
        
        while ServerDatabaseService.check_slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
            
        return slug
    
    @staticmethod
    def create_server(server_data: Dict[str, Any]) -> str:
        """Create a new server in the database and return the server ID"""
        server_id = str(uuid.uuid4())
        
        insert_query = """
            INSERT INTO servers (
                id, user_id, name, slug, description, version, 
                status, visibility, source_code, tags, category, 
                total_requests, is_featured, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
        """
        
        # Convert tags to JSON string if provided
        tags_json = json.dumps(server_data.get('tags')) if server_data.get('tags') else None
        
        supabase_client.execute_query(insert_query, (
            server_id,
            server_data['user_id'],
            server_data['name'],
            server_data['slug'],
            server_data.get('description', ''),
            server_data.get('version', '1.0.0'),
            server_data.get('status', 'active'),
            server_data.get('visibility', 'private'),
            server_data['source_code'],
            tags_json,
            server_data.get('category', 'general'),
            0,  # total_requests
            False  # is_featured
        ))
        
        return server_id
    
    @staticmethod
    def get_server_by_id(server_id: str) -> Optional[Dict[str, Any]]:
        """Get server data by ID"""
        query = """
            SELECT id, name, slug, description, version, status, visibility, 
                   category, tags, created_at
            FROM servers 
            WHERE id = %s
        """
        result = supabase_client.execute_query(query, (server_id,))
        
        if not result:
            return None
            
        server_data = dict(result[0])
        
        # Convert datetime to string for JSON serialization
        if 'created_at' in server_data and server_data['created_at']:
            server_data['created_at'] = server_data['created_at'].isoformat()
        
        # Parse tags JSON if present
        if server_data.get('tags'):
            try:
                server_data['tags'] = json.loads(server_data['tags'])
            except:
                server_data['tags'] = []
        
        return server_data
    
    @staticmethod
    def get_server_by_slug(slug: str) -> Optional[Dict[str, Any]]:
        """Get server data by slug"""
        query = """
            SELECT id, name, slug, description, version, status, created_at
            FROM servers 
            WHERE slug = %s
        """
        result = supabase_client.execute_query(query, (slug,))
        
        if not result:
            return None
            
        server_data = dict(result[0])
        
        # Convert datetime to string for JSON serialization
        if 'created_at' in server_data and server_data['created_at']:
            server_data['created_at'] = server_data['created_at'].isoformat()
            
        return server_data
    
    @staticmethod
    def list_active_servers() -> List[Dict[str, Any]]:
        """List all active servers"""
        query = """
            SELECT id, name, slug, description, version, status
            FROM servers 
            WHERE status = 'active'
            ORDER BY created_at DESC
        """
        result = supabase_client.execute_query(query)
        
        return [dict(row) for row in result] if result else []
    
    @staticmethod
    def get_server_with_source_code(slug: str) -> Optional[Dict[str, Any]]:
        """Get server with source code for execution"""
        query = """
            SELECT id, name, slug, source_code, status
            FROM servers 
            WHERE slug = %s AND status = 'active'
        """
        result = supabase_client.execute_query(query, (slug,))
        
        if not result:
            return None
            
        return dict(result[0])
    
    @staticmethod
    def create_server_files(server_id: str, files: List[Dict[str, str]]) -> None:
        """Create multiple files for a server"""
        for file_data in files:
            file_id = str(uuid.uuid4())
            insert_query = """
                INSERT INTO server_files (id, server_id, filename, content, file_type, created_at) 
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            supabase_client.execute_query(insert_query, (
                file_id,
                server_id,
                file_data['filename'],
                file_data['content'],
                file_data.get('file_type', 'python')
            ))
    
    @staticmethod
    def get_server_files(server_slug: str) -> List[Dict[str, Any]]:
        """Get all files for a server by slug"""
        query = """
            SELECT sf.filename, sf.content, sf.file_type, sf.created_at
            FROM server_files sf
            JOIN servers s ON sf.server_id = s.id
            WHERE s.slug = %s AND s.status = 'active'
            ORDER BY sf.filename
        """
        result = supabase_client.execute_query(query, (server_slug,))
        return [dict(row) for row in result] if result else []
    
    @staticmethod
    def get_server_with_files(server_slug: str) -> Optional[Dict[str, Any]]:
        """Get server with all its files for execution"""
        # First get server info
        server_query = """
            SELECT id, name, slug, status, source_code
            FROM servers 
            WHERE slug = %s AND status = 'active'
        """
        server_result = supabase_client.execute_query(server_query, (server_slug,))
        
        if not server_result:
            return None
        
        server_data = dict(server_result[0])
        
        # Get files for this server
        files = ServerDatabaseService.get_server_files(server_slug)
        server_data['files'] = files
        
        # Check if we have files or just legacy source_code
        server_data['has_multiple_files'] = len(files) > 0
        
        return server_data
    
    @staticmethod
    def update_server_files(server_id: str, files: List[Dict[str, str]]) -> None:
        """Update server files by deleting old ones and creating new ones"""
        # Delete existing files
        delete_query = "DELETE FROM server_files WHERE server_id = %s"
        supabase_client.execute_query(delete_query, (server_id,))
        
        # Create new files
        ServerDatabaseService.create_server_files(server_id, files)
    
    @staticmethod
    def delete_server_files(server_id: str) -> None:
        """Delete all files for a server"""
        delete_query = "DELETE FROM server_files WHERE server_id = %s"
        supabase_client.execute_query(delete_query, (server_id,))