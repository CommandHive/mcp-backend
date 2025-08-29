import os
import sys
import importlib.util
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP


class MultiFileServerLoader:
    """Handles loading MCP servers from multiple files stored in database"""
    
    def __init__(self, base_path: str = "/tmp/mcp_servers"):
        """Initialize loader with base path for server files"""
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True, mode=0o755)
        self.loaded_modules: Dict[str, Any] = {}
    
    def _sanitize_path(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal attacks"""
        # Remove any path traversal attempts
        clean_name = os.path.basename(filename)
        # Remove any potentially dangerous characters
        clean_name = clean_name.replace('..', '').replace('~', '')
        return clean_name
    
    def _create_server_directory(self, server_slug: str) -> Path:
        """Create and return server directory path"""
        server_dir = self.base_path / server_slug
        
        # Clean up existing directory if it exists
        if server_dir.exists():
            shutil.rmtree(server_dir)
        
        server_dir.mkdir(parents=True, exist_ok=True)
        return server_dir
    
    def _write_server_files(self, server_dir: Path, server_files: List[Dict[str, Any]]) -> None:
        """Write server files to the directory"""
        for file_data in server_files:
            filename = self._sanitize_path(file_data['filename'])
            content = file_data['content']
            
            file_path = server_dir / filename
            
            # Create subdirectories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            try:
                file_path.write_text(content, encoding='utf-8')
                print(f"Written file: {file_path}")
            except Exception as e:
                print(f"Error writing file {filename}: {e}")
                raise
    
    def _install_requirements(self, server_dir: Path) -> None:
        """Install requirements.txt if it exists"""
        requirements_file = server_dir / "requirements.txt"
        
        if requirements_file.exists():
            try:
                import subprocess
                print(f"Installing requirements from {requirements_file}")
                
                # Create a virtual environment or install to current environment
                subprocess.run([
                    sys.executable, "-m", "pip", "install", 
                    "-r", str(requirements_file),
                    "--quiet"  # Reduce output noise
                ], check=True, cwd=server_dir)
                
                print("Requirements installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to install requirements: {e}")
                # Don't fail completely, as server might still work
    
    def _import_server_module(self, server_dir: Path, server_slug: str) -> FastMCP:
        """Import the server module and return FastMCP instance"""
        main_file = server_dir / "main.py"
        
        if not main_file.exists():
            raise ValueError(f"main.py not found in server {server_slug}")
        
        # Add server directory to Python path
        server_dir_str = str(server_dir)
        if server_dir_str not in sys.path:
            sys.path.insert(0, server_dir_str)
        
        try:
            # Create unique module name to avoid conflicts
            module_name = f"mcp_server_{server_slug.replace('-', '_')}"
            
            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, main_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load spec from {main_file}")
            
            module = importlib.util.module_from_spec(spec)
            
            # Store reference to prevent garbage collection
            self.loaded_modules[server_slug] = module
            
            # Execute the module
            spec.loader.exec_module(module)
            
            # Look for FastMCP instance in module
            mcp_server = None
            
            # Common variable names to check
            possible_names = ['app', 'server', 'mcp', 'mcp_server', 'fastmcp']
            
            for var_name in possible_names:
                if hasattr(module, var_name):
                    var_value = getattr(module, var_name)
                    if isinstance(var_value, FastMCP):
                        mcp_server = var_value
                        print(f"Found FastMCP instance: {var_name}")
                        break
            
            # If not found in common names, search all module attributes
            if mcp_server is None:
                for var_name in dir(module):
                    if not var_name.startswith('_'):
                        var_value = getattr(module, var_name)
                        if isinstance(var_value, FastMCP):
                            mcp_server = var_value
                            print(f"Found FastMCP instance: {var_name}")
                            break
            
            if mcp_server is None:
                raise ValueError(f"No FastMCP instance found in server {server_slug}")
            
            return mcp_server
            
        except Exception as e:
            print(f"Error importing server module {server_slug}: {e}")
            raise
        finally:
            # Clean up Python path
            if server_dir_str in sys.path:
                sys.path.remove(server_dir_str)
    
    async def load_server_from_files(self, server_slug: str, server_files: List[Dict[str, Any]]) -> FastMCP:
        """Load server from multiple files"""
        try:
            print(f"Loading multi-file server: {server_slug}")
            
            # Create server directory
            server_dir = self._create_server_directory(server_slug)
            
            # Write all files to disk
            self._write_server_files(server_dir, server_files)
            
            # Install requirements if present
            self._install_requirements(server_dir)
            
            # Import and return FastMCP instance
            mcp_server = self._import_server_module(server_dir, server_slug)
            
            print(f"Successfully loaded multi-file server: {server_slug}")
            return mcp_server
            
        except Exception as e:
            print(f"Error loading multi-file server {server_slug}: {e}")
            # Clean up on failure
            self.cleanup_server_files(server_slug)
            raise
    
    def cleanup_server_files(self, server_slug: str) -> None:
        """Clean up server files and module references"""
        try:
            # Remove from loaded modules
            if server_slug in self.loaded_modules:
                del self.loaded_modules[server_slug]
            
            # Remove directory
            server_dir = self.base_path / server_slug
            if server_dir.exists():
                shutil.rmtree(server_dir)
                print(f"Cleaned up files for server: {server_slug}")
                
        except Exception as e:
            print(f"Error cleaning up server {server_slug}: {e}")
    
    def cleanup_all_servers(self) -> None:
        """Clean up all server files and modules"""
        try:
            # Clear loaded modules
            self.loaded_modules.clear()
            
            # Remove base directory
            if self.base_path.exists():
                shutil.rmtree(self.base_path)
                self.base_path.mkdir(exist_ok=True, mode=0o755)
                
            print("Cleaned up all server files")
            
        except Exception as e:
            print(f"Error cleaning up all servers: {e}")