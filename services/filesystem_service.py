"""
Filesystem service for managing MCP server files
Handles creation, management, and cleanup of server directories and files
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class FilesystemService:
    """Service for managing MCP server files on the filesystem"""
    
    def __init__(self, base_path: str = "mcp_servers"):
        """Initialize with base path for server storage"""
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True, mode=0o755)
    
    def _sanitize_path_component(self, component: str) -> str:
        """Sanitize a path component to prevent directory traversal"""
        # Remove dangerous characters and path traversal attempts
        sanitized = component.replace('..', '').replace('/', '').replace('\\', '')
        sanitized = ''.join(c for c in sanitized if c.isalnum() or c in '-_.')
        return sanitized or 'default'
    
    def _create_server_path(self, user_id: str, server_slug: str) -> Path:
        """Create and return the server directory path"""
        user_id_clean = self._sanitize_path_component(user_id)
        server_slug_clean = self._sanitize_path_component(server_slug)
        
        user_dir = self.base_path / user_id_clean
        server_dir = user_dir / server_slug_clean
        
        return server_dir
    
    def create_server_directory(self, user_id: str, server_slug: str) -> str:
        """Create a new server directory and return the path"""
        server_dir = self._create_server_path(user_id, server_slug)
        
        # Remove existing directory if it exists
        if server_dir.exists():
            shutil.rmtree(server_dir)
        
        # Create directory structure
        server_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
        
        return str(server_dir)
    
    def write_server_files(self, folder_path: str, files: List[Dict[str, Any]]) -> List[str]:
        """
        Write files to server directory
        Returns list of created file paths
        """
        server_dir = Path(folder_path)
        if not server_dir.exists():
            raise ValueError(f"Server directory does not exist: {folder_path}")
        
        created_files = []
        
        for file_data in files:
            filename = file_data.get('filename', '')
            content = file_data.get('content', '')
            
            if not filename:
                continue
            
            # Sanitize filename
            clean_filename = self._sanitize_filename(filename)
            if not clean_filename:
                continue
            
            # Create file path
            file_path = server_dir / clean_filename
            
            # Create subdirectories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                # Write file content
                file_path.write_text(content, encoding='utf-8')
                created_files.append(str(file_path))
                print(f"Created file: {file_path}")
            except Exception as e:
                print(f"Error writing file {clean_filename}: {e}")
                # Don't fail completely, continue with other files
        
        return created_files
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent security issues"""
        # Remove path traversal attempts
        clean_name = os.path.basename(filename)
        
        # Remove dangerous characters but allow forward slashes for subdirectories
        clean_name = clean_name.replace('..', '').replace('~', '')
        
        # Ensure filename is not empty and has valid characters
        if not clean_name or clean_name.startswith('.'):
            return ''
        
        # Allow alphanumeric, dots, hyphens, underscores, and forward slashes
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_/')
        clean_name = ''.join(c for c in clean_name if c in allowed_chars)
        
        return clean_name
    
    def read_server_files(self, folder_path: str) -> List[Dict[str, Any]]:
        """Read all files from a server directory"""
        server_dir = Path(folder_path)
        if not server_dir.exists():
            return []
        
        files = []
        
        # Recursively find all files
        for file_path in server_dir.rglob('*'):
            if file_path.is_file():
                try:
                    # Get relative path from server directory
                    relative_path = file_path.relative_to(server_dir)
                    
                    # Read file content
                    content = file_path.read_text(encoding='utf-8')
                    
                    files.append({
                        'filename': str(relative_path),
                        'content': content,
                        'file_type': self._get_file_type(file_path.suffix),
                        'file_path': str(file_path)
                    })
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    continue
        
        return files
    
    def _get_file_type(self, extension: str) -> str:
        """Determine file type from extension"""
        extension = extension.lower()
        type_mapping = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.json': 'json',
            '.txt': 'text',
            '.md': 'markdown',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.toml': 'toml'
        }
        return type_mapping.get(extension, 'text')
    
    def copy_server_directory(self, source_folder_path: str, target_user_id: str, 
                             target_server_slug: str) -> str:
        """Copy a server directory to a new location"""
        source_dir = Path(source_folder_path)
        if not source_dir.exists():
            raise ValueError(f"Source directory does not exist: {source_folder_path}")
        
        # Create target directory
        target_folder_path = self.create_server_directory(target_user_id, target_server_slug)
        target_dir = Path(target_folder_path)
        
        # Copy all files
        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
        
        return target_folder_path
    
    def delete_server_directory(self, folder_path: str) -> bool:
        """Delete a server directory and all its contents"""
        try:
            server_dir = Path(folder_path)
            if server_dir.exists():
                shutil.rmtree(server_dir)
                print(f"Deleted server directory: {folder_path}")
                return True
            return False
        except Exception as e:
            print(f"Error deleting server directory {folder_path}: {e}")
            return False
    
    def get_server_main_file(self, folder_path: str) -> Optional[str]:
        """Get the content of the main.py file"""
        main_file = Path(folder_path) / "main.py"
        if main_file.exists():
            try:
                return main_file.read_text(encoding='utf-8')
            except Exception as e:
                print(f"Error reading main.py: {e}")
        return None
    
    def update_server_files(self, folder_path: str, files: List[Dict[str, Any]]) -> List[str]:
        """Update server files (delete old ones and write new ones)"""
        server_dir = Path(folder_path)
        if not server_dir.exists():
            raise ValueError(f"Server directory does not exist: {folder_path}")
        
        # Clear existing files (except hidden files like .git)
        for item in server_dir.iterdir():
            if not item.name.startswith('.'):
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        # Write new files
        return self.write_server_files(folder_path, files)
    
    def ensure_user_directory(self, user_id: str) -> str:
        """Ensure user directory exists and return path"""
        user_id_clean = self._sanitize_path_component(user_id)
        user_dir = self.base_path / user_id_clean
        user_dir.mkdir(exist_ok=True, mode=0o755)
        return str(user_dir)
    
    def list_user_servers(self, user_id: str) -> List[str]:
        """List all server directories for a user"""
        user_id_clean = self._sanitize_path_component(user_id)
        user_dir = self.base_path / user_id_clean
        
        if not user_dir.exists():
            return []
        
        servers = []
        for item in user_dir.iterdir():
            if item.is_dir():
                servers.append(item.name)
        
        return servers


# Global instance
filesystem_service = FilesystemService()