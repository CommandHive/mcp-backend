import os
import sys
import importlib.util
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP


class MultiFileServerLoader:
    """Handles loading MCP servers from persistent filesystem directories"""
    
    def __init__(self, base_path: str = "mcp_servers"):
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
    
    def _get_server_directory(self, folder_path: str) -> Path:
        """Get server directory path from folder_path"""
        server_dir = Path(folder_path)
        
        if not server_dir.exists():
            raise ValueError(f"Server directory does not exist: {folder_path}")
        
        return server_dir
    
    def _validate_server_files(self, server_dir: Path) -> None:
        """Validate that server directory has required files"""
        main_file = server_dir / "main.py"
        if not main_file.exists():
            raise ValueError(f"main.py not found in server directory: {server_dir}")
        
        # Validate that main.py contains FastMCP instance
        try:
            content = main_file.read_text(encoding='utf-8')
            if 'FastMCP' not in content:
                raise ValueError("main.py must contain a FastMCP instance")
        except Exception as e:
            raise ValueError(f"Error validating main.py: {e}")
    
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
    
    async def load_server_from_folder(self, server_slug: str, folder_path: str) -> FastMCP:
        """Load server from persistent filesystem folder"""
        try:
            print(f"Loading server from folder: {server_slug} -> {folder_path}")
            
            # Get server directory
            server_dir = self._get_server_directory(folder_path)
            
            # Validate server files
            self._validate_server_files(server_dir)
            
            # Install requirements if present
            self._install_requirements(server_dir)
            
            # Import and return FastMCP instance
            mcp_server = self._import_server_module(server_dir, server_slug)
            
            print(f"Successfully loaded server: {server_slug}")
            return mcp_server
            
        except Exception as e:
            print(f"Error loading server {server_slug}: {e}")
            raise
    
    def cleanup_server_module(self, server_slug: str) -> None:
        """Clean up server module references (but keep files on disk)"""
        try:
            # Remove from loaded modules
            if server_slug in self.loaded_modules:
                del self.loaded_modules[server_slug]
                print(f"Cleaned up module for server: {server_slug}")
                
        except Exception as e:
            print(f"Error cleaning up server module {server_slug}: {e}")
    
    def cleanup_all_modules(self) -> None:
        """Clean up all loaded modules (but keep files on disk)"""
        try:
            # Clear loaded modules
            self.loaded_modules.clear()
            print("Cleaned up all loaded modules")
            
        except Exception as e:
            print(f"Error cleaning up all modules: {e}")