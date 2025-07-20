import contextlib
import json
from typing import Dict
from starlette.routing import Router, Mount, Route
from starlette.responses import JSONResponse, Response
from starlette.applications import Starlette

from mcp.server.fastmcp import FastMCP
from services.server_db_service import ServerDatabaseService
from services.server_service import ServerService


class DynamicMCPManager:
    def __init__(self):
        self.active_servers: Dict[str, FastMCP] = {}
        self.session_managers: Dict[str, contextlib.AsyncExitStack] = {}
    
    async def load_server_from_db(self, server_slug: str) -> FastMCP:
        """Load an MCP server from database and execute its code"""
        try:
            # Get server configuration from database by slug
            server_data = ServerDatabaseService.get_server_with_source_code(server_slug)
            print(f"result from database query {server_data}")
            
            if not server_data:
                raise ValueError(f"Server with slug '{server_slug}' not found or inactive")
            
            source_code = server_data.get('source_code')
            print(f"source code to be executed {source_code}")
            if not source_code:
                raise ValueError(f"No source code found for server {server_slug}")
            
            # Execute the source code to create the MCP server
            exec_globals = {'FastMCP': FastMCP}
            exec(source_code, exec_globals)
            
            # Find the created MCP server instance
            mcp_server = None
            for var_name, var_value in exec_globals.items():
                if isinstance(var_value, FastMCP):
                    mcp_server = var_value
                    break
            
            if not mcp_server:
                raise ValueError(f"No FastMCP instance found in server {server_slug} source code")
            
            streamable_app = mcp_server.streamable_http_app()
            # Start the session manager for this server
            stack = contextlib.AsyncExitStack()
            await stack.enter_async_context(mcp_server.session_manager.run())
            self.session_managers[server_slug] = stack
            
            return mcp_server
            
        except Exception as e:
            print(f"Error loading server {server_slug}: {e}")
            raise
    
    async def get_or_create_server(self, server_slug: str) -> FastMCP:
        """Get existing server or create new one from database"""
        if server_slug not in self.active_servers:
            self.active_servers[server_slug] = await self.load_server_from_db(server_slug)
        return self.active_servers[server_slug]
    
    async def cleanup_server(self, server_slug: str):
        """Cleanup server resources"""
        if server_slug in self.session_managers:
            await self.session_managers[server_slug].aclose()
            del self.session_managers[server_slug]
        
        if server_slug in self.active_servers:
            del self.active_servers[server_slug]


# Global instance
mcp_manager = DynamicMCPManager()


async def dynamic_mcp_handler(request):
    """Handle dynamic MCP server requests"""
    print(request)
    try:
        server_slug = request.path_params.get('slug')
        server_slug = server_slug.replace("/mcp", "")
        # Get or create the MCP server
        mcp_server = await mcp_manager.get_or_create_server(server_slug)
        
        # Forward the request to the MCP server's streamable HTTP app
        streamable_app = mcp_server.streamable_http_app()
        
        # Create a new request with the path stripped of the slug prefix
        path_info = request.url.path.replace(f'/{server_slug}', '') or '/'
        
        # Create a modified scope for the streamable app
        scope = dict(request.scope)
        scope['path'] = path_info
        scope['path_info'] = path_info
        
        # Call the streamable app directly (it handles sending the response)
        await streamable_app(scope, request.receive, request._send)
        
        # Return an empty response since streamable app already handled the response
        class EmptyResponse:
            async def __call__(self, scope, receive, send):
                pass
        
        return EmptyResponse()
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


async def list_servers_handler(request):
    """List all active servers"""
    try:
        servers = ServerDatabaseService.list_active_servers()
        
        return JSONResponse({
            "status": "success",
            "servers": servers,
            "count": len(servers)
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error", 
            "message": str(e)
        }, status_code=500)




async def get_server_info_handler(request):
    """Get server information by slug"""
    try:
        server_slug = request.path_params.get('slug')
        server_data = ServerDatabaseService.get_server_by_slug(server_slug)
        
        if not server_data:
            return JSONResponse({
                "status": "error",
                "message": "Server not found"
            }, status_code=404)
        
        return JSONResponse({
            "status": "success",
            "server": server_data
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


async def create_mcp_server_handler(request):
    """Create a new MCP server with generated code"""
    try:
        body = await request.json()
        
        # Use the server service to create the server
        server_data = ServerService.create_server(body)
        
        return JSONResponse({
            "status": "success",
            "message": "MCP server created successfully",
            "server": server_data
        }, status_code=201)
        
    except ValueError as e:
        # Validation errors
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=400)
    except json.JSONDecodeError:
        return JSONResponse({
            "status": "error",
            "message": "Invalid JSON in request body"
        }, status_code=400)
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"Failed to create server: {str(e)}"
        }, status_code=500)


router = Router([
    Route("/", list_servers_handler, methods=["GET"]),
    Route("/create", create_mcp_server_handler, methods=["POST"]),
    Route("/info/{slug}", get_server_info_handler, methods=["GET"]),
    Route("/{slug:path}", dynamic_mcp_handler, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
])