import contextlib
import json
from typing import Dict
from starlette.routing import Router, Mount, Route
from starlette.responses import JSONResponse, Response
from starlette.applications import Starlette

from mcp.server.fastmcp import FastMCP
from services.server_db_service import ServerDatabaseService
from services.server_service import ServerService
from services.blockchain_client import log_tool_call_to_blockchain
from services.multi_file_server_loader import MultiFileServerLoader


class DynamicMCPManager:
    def __init__(self):
        self.active_servers: Dict[str, FastMCP] = {}
        self.session_managers: Dict[str, contextlib.AsyncExitStack] = {}
        self.file_loader = MultiFileServerLoader()
    
    async def load_server_from_db(self, server_slug: str) -> FastMCP:
        """Load an MCP server from database and execute its code"""
        try:
            # Get server configuration with folder path from database by slug
            server_data = ServerDatabaseService.get_server_with_files(server_slug)
            print(f"result from database query {server_data}")
            
            if not server_data:
                raise ValueError(f"Server with slug '{server_slug}' not found or inactive")
            
            # Get folder path from server data
            folder_path = server_data.get('folder_path')
            if not folder_path:
                raise ValueError(f"No folder path found for server {server_slug}")
            
            print(f"Loading server from folder: {server_slug} -> {folder_path}")
            
            # Load server from persistent folder
            mcp_server = await self.file_loader.load_server_from_folder(server_slug, folder_path)
            
            if not mcp_server:
                raise ValueError(f"No FastMCP instance found in server {server_slug}")
            
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
        
        # Clean up module references (but keep files)
        self.file_loader.cleanup_server_module(server_slug)


# Global instance
mcp_manager = DynamicMCPManager()


async def custom_pre_tool_function():
    """Custom function that executes before any tool call"""
    print("🚀 CUSTOM FUNCTION: Hello World! Executing before tool call...")
    # Add any custom logic here
    return {"message": "Custom pre-processing completed"}

async def dynamic_mcp_handler(request):
    """Handle dynamic MCP server requests"""
    print(request)
    print(f"{request.method} {request.url} headers={dict(request.headers)}")
    
    # Create a custom receive that can intercept and log the body
    original_receive = request.receive
    body_data = b""
    
    async def logging_receive():
        nonlocal body_data
        message = await original_receive()
        
        if message["type"] == "http.request":
            chunk = message.get("body", b"")
            body_data += chunk
            
            # If this is the last chunk, process it
            if not message.get("more_body", True):
                try:
                    import json
                    payload_str = body_data.decode('utf-8')
                    print(f"Request body: {payload_str}")
                    
                    # Skip parsing if body is empty (GET requests, etc.)
                    if not payload_str.strip():
                        return message
                    
                    payload = json.loads(payload_str)
                    print(f"Parsed payload: {payload}")
                    
                    # Check if this is a tool call
                    if payload.get("method") == "tools/call":
                        print("🔧 TOOL CALL DETECTED!")
                        
                        # Extract tool call information
                        params = payload.get("params", {})
                        tool_name = params.get("name", "unknown_tool")
                        
                        # Log to blockchain
                        blockchain_result = await log_tool_call_to_blockchain(
                            mcp_id=server_slug,
                            tool_call_name=tool_name,
                            client_info="MCP Backend v1.0"
                        )
                        
                        # Execute custom function
                        custom_result = await custom_pre_tool_function()
                        print(f"Custom function result: {custom_result}")
                        print(f"Blockchain result: {blockchain_result}")
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    print(f"Could not parse payload: {e}")
        
        return message
    
    # Replace the receive method
    request._receive = logging_receive
    
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


# -------------------------------------------------------------
# cURL examples for /servers routes (requires JWT Authorization)
# -------------------------------------------------------------
#
# Helpful env vars for brevity:
#   export BASE_URL="http://localhost:8000"
#   export JWT="<YOUR_JWT_TOKEN>"
#
# 1) List active servers
#   curl -s -X GET "$BASE_URL/servers/" \
#        -H "Authorization: Bearer $JWT"
#
# 2) Get server info by slug
#   curl -s -X GET "$BASE_URL/servers/info/<slug>" \
#        -H "Authorization: Bearer $JWT"
#
# 3a) Create a new MCP server (legacy single-file approach)
#   curl -s -X POST "$BASE_URL/servers/create" \
#        -H "Authorization: Bearer $JWT" \
#        -H "Content-Type: application/json" \
#        -d '{
#              "name": "Demo Server",
#              "user_id": "00000000-0000-0000-0000-000000000000",
#              "source_code": "app = FastMCP('demo-server')",
#              "description": "My demo MCP server",
#              "version": "1.0.0",
#              "visibility": "private",
#              "category": "general",
#              "tags": ["demo", "test"]
#            }'
#
# 3b) Create a new MCP server (multi-file approach - RECOMMENDED)
#   curl -s -X POST "$BASE_URL/servers/create" \
#        -H "Authorization: Bearer $JWT" \
#        -H "Content-Type: application/json" \
#        -d '{
#              "name": "Multi-File Demo Server",
#              "user_id": "00000000-0000-0000-0000-000000000000",
#              "files": [
#                {
#                  "filename": "main.py",
#                  "content": "from mcp.server.fastmcp import FastMCP\nfrom utils import helper_function\n\napp = FastMCP('demo-server')\n\n@app.tool()\ndef greet(name: str) -> str:\n    return helper_function(name)\n",
#                  "file_type": "python"
#                },
#                {
#                  "filename": "utils.py",
#                  "content": "def helper_function(name: str) -> str:\n    return f'Hello, {name}!'\n",
#                  "file_type": "python"
#                },
#                {
#                  "filename": "requirements.txt",
#                  "content": "requests==2.31.0\n",
#                  "file_type": "text"
#                }
#              ],
#              "description": "Multi-file demo MCP server",
#              "version": "1.0.0",
#              "visibility": "private",
#              "category": "general",
#              "tags": ["demo", "multifile"]
#            }'
#
#    Notes:
#    - Required fields: name, user_id, and either source_code OR files array
#    - For multi-file: files array must contain main.py with FastMCP instance
#    - For single-file: source_code must create a FastMCP instance
#    - Multi-file approach supports requirements.txt for dependencies
#
# 4) Proxy requests to a dynamic MCP server (generic pass-through)
#    Root of MCP app (GET):
#      curl -s -X GET "$BASE_URL/servers/<slug>/mcp" \
#           -H "Authorization: Bearer $JWT"
#
#    Example POST to an MCP subpath:
#      curl -s -X POST "$BASE_URL/servers/<slug>/mcp/some/path" \
#           -H "Authorization: Bearer $JWT" \
#           -H "Content-Type: application/json" \
#           -d '{"foo":"bar"}'
#
#    Supported methods for the dynamic route: GET, POST, PUT, DELETE, PATCH
# -------------------------------------------------------------