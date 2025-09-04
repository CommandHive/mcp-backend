import sys
import importlib.util
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from mcp.server.fastmcp import FastMCP


class MCPExecutionService:
    """Service for executing MCP server files and tools from disk"""
    
    def __init__(self):
        self.loaded_modules = {}  # Cache for loaded modules
    
    def load_mcp_server_module(self, session_dir: str) -> Any:
        """
        Load MCP server module from session directory
        
        Args:
            session_dir: Path to session directory containing main.py
            
        Returns:
            Loaded module object
        """
        session_path = Path(session_dir)
        main_py = session_path / "main.py"
        
        if not main_py.exists():
            raise FileNotFoundError(f"main.py not found in {session_dir}")
        
        # Use session_dir as module identifier
        module_id = f"mcp_server_{session_path.name}"
        
        # Check if already loaded
        if module_id in self.loaded_modules:
            return self.loaded_modules[module_id]
        
        try:
            # Load module from file
            spec = importlib.util.spec_from_file_location(module_id, main_py)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module spec from {main_py}")
            
            module = importlib.util.module_from_spec(spec)
            
            # Add session directory to Python path temporarily
            original_path = sys.path.copy()
            sys.path.insert(0, str(session_path))
            
            try:
                # Execute the module
                spec.loader.exec_module(module)
                
                # Cache the loaded module
                self.loaded_modules[module_id] = module
                
                print(f"Successfully loaded MCP server module from {session_dir}")
                return module
                
            finally:
                # Restore original Python path
                sys.path[:] = original_path
                
        except Exception as e:
            print(f"Error loading MCP server module: {e}")
            print(traceback.format_exc())
            raise RuntimeError(f"Failed to load MCP server: {str(e)}")
    
    def discover_fastmcp_instances(self, module: Any) -> List[FastMCP]:
        """
        Discover FastMCP instances in loaded module
        
        Args:
            module: Loaded module object
            
        Returns:
            List of FastMCP instances found in module
        """
        fastmcp_instances = []
        
        for attr_name in dir(module):
            if not attr_name.startswith('_'):
                attr_value = getattr(module, attr_name)
                if isinstance(attr_value, FastMCP):
                    fastmcp_instances.append(attr_value)
                    print(f"Found FastMCP instance: {attr_name}")
        
        return fastmcp_instances
    
    def get_available_tools(self, session_dir: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all available tools from MCP server
        
        Args:
            session_dir: Path to session directory
            
        Returns:
            Dictionary of tool names and their metadata
        """
        try:
            module = self.load_mcp_server_module(session_dir)
            fastmcp_instances = self.discover_fastmcp_instances(module)
            
            all_tools = {}
            
            for instance in fastmcp_instances:
                if hasattr(instance, '_tool_manager') and hasattr(instance._tool_manager, '_tools'):
                    tools = instance._tool_manager._tools
                    
                    for tool_name, tool_obj in tools.items():
                        all_tools[tool_name] = {
                            'name': tool_name,
                            'description': getattr(tool_obj, 'description', ''),
                            'function': tool_obj.fn,
                            'parameters': getattr(tool_obj, 'parameters', None),
                            'instance': instance
                        }
            
            print(f"Discovered {len(all_tools)} tools: {list(all_tools.keys())}")
            return all_tools
            
        except Exception as e:
            print(f"Error discovering tools: {e}")
            raise
    
    def execute_tool(self, session_dir: str, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a specific tool from MCP server
        
        Args:
            session_dir: Path to session directory containing MCP server
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Result from tool execution
        """
        try:
            # Get available tools
            available_tools = self.get_available_tools(session_dir)
            
            if tool_name not in available_tools:
                available_tool_names = list(available_tools.keys())
                raise ValueError(f"Tool '{tool_name}' not found. Available tools: {available_tool_names}")
            
            tool_info = available_tools[tool_name]
            tool_function = tool_info['function']
            
            print(f"Executing tool '{tool_name}' with parameters: {parameters}")
            
            # Execute the tool
            try:
                result = tool_function(**parameters)
                print(f"Tool '{tool_name}' executed successfully")
                return result
                
            except TypeError as e:
                # Handle parameter mismatch
                raise ValueError(f"Invalid parameters for tool '{tool_name}': {str(e)}")
                
        except Exception as e:
            print(f"Error executing tool '{tool_name}': {e}")
            print(traceback.format_exc())
            raise
    
    def validate_session_directory(self, session_dir: str) -> bool:
        """
        Validate that session directory contains a valid MCP server
        
        Args:
            session_dir: Path to session directory
            
        Returns:
            True if valid MCP server found
        """
        try:
            session_path = Path(session_dir)
            
            # Check if directory exists
            if not session_path.exists():
                return False
            
            # Check if main.py exists
            main_py = session_path / "main.py"
            if not main_py.exists():
                return False
            
            # Try to load and validate the module
            module = self.load_mcp_server_module(session_dir)
            fastmcp_instances = self.discover_fastmcp_instances(module)
            
            # Must have at least one FastMCP instance
            return len(fastmcp_instances) > 0
            
        except Exception as e:
            print(f"Session validation failed: {e}")
            return False
    
    def cleanup_module_cache(self, session_dir: str = None):
        """
        Clean up cached modules
        
        Args:
            session_dir: Specific session to clean up, or None for all
        """
        if session_dir:
            session_path = Path(session_dir)
            module_id = f"mcp_server_{session_path.name}"
            if module_id in self.loaded_modules:
                del self.loaded_modules[module_id]
                print(f"Cleaned up cached module for {session_dir}")
        else:
            self.loaded_modules.clear()
            print("Cleaned up all cached modules")


# Singleton instance
mcp_execution_service = MCPExecutionService()