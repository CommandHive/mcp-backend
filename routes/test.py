"""
Run from the repository root:
    uvicorn examples.snippets.servers.streamable_starlette_mount:app --reload
"""

import contextlib
import asyncio
from typing import Dict, Optional, Tuple
from starlette.applications import Starlette
from starlette.routing import Route, Mount, Router
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.types import Scope, Receive, Send

from mcp.server.fastmcp import FastMCP
from services.server_code_service import ServerCodeService

# ---------- Built-in demo servers ----------

# Echo server
echo_mcp = FastMCP(name="EchoServer", stateless_http=True)

@echo_mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@echo_mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

@echo_mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting", 
        "casual": "Please write a casual, relaxed greeting"
    }
    return f"{styles.get(style, styles['friendly'])} for someone named {name}."


# Math server
math_mcp = FastMCP(name="MathServer", stateless_http=True)

@math_mcp.tool()
def add_two(n: int) -> int:
    """Tool to add two to the input"""
    return n + 2


# ---------- Server Registry for Dynamic Servers ----------

class ServerRegistry:
    def __init__(self):
        self._servers: Dict[str, Tuple[FastMCP, contextlib.AsyncExitStack]] = {}
        self._lock = asyncio.Lock()
    
    async def get_server(self, server_id: str) -> Optional[FastMCP]:
        """Get or create a server instance, ensuring its session manager is running."""
        async with self._lock:
            if server_id in self._servers:
                return self._servers[server_id][0]
            
            # Load server from database
            loaded, dynamic = self._load_server_by_id(server_id)
            if loaded is None and dynamic is None:
                return None
            
            mcp_server = loaded or dynamic
            
            # Initialize session manager
            try:
                stack = contextlib.AsyncExitStack()
                # Initialize the streamable HTTP app to create the session manager
                mcp_server.streamable_http_app()
                await stack.enter_async_context(mcp_server.session_manager.run())
                self._servers[server_id] = (mcp_server, stack)
                print(f"[ServerRegistry] Initialized server: {mcp_server.name}")
                return mcp_server
            except Exception as e:
                print(f"[ServerRegistry] Failed to initialize server {server_id}: {e}")
                return None
    
    async def remove_server(self, server_id: str):
        """Remove and cleanup a server."""
        async with self._lock:
            if server_id in self._servers:
                _, stack = self._servers[server_id]
                await stack.aclose()
                del self._servers[server_id]
                print(f"[ServerRegistry] Removed server: {server_id}")
    
    async def shutdown_all(self):
        """Shutdown all registered servers."""
        async with self._lock:
            for server_id, (server, stack) in self._servers.items():
                try:
                    await stack.aclose()
                    print(f"[ServerRegistry] Shutdown server: {server.name}")
                except Exception as e:
                    print(f"[ServerRegistry] Error shutting down server {server_id}: {e}")
            self._servers.clear()
    
    def _load_server_by_id(self, server_id: str) -> Tuple[Optional[FastMCP], Optional[FastMCP]]:
        """
        Load MCP server source by id.
        - If source defines a FastMCP instance, return it.
        - Otherwise, attach discovered callables to a new FastMCP.
        Returns tuple: (loaded_mcp, dynamic_mcp) where only one is non-None if successful.
        """
        print(f"[ServerRegistry] Loading server from DB: {server_id}")
        try:
            source_code = ServerCodeService.get_source_code_by_id(server_id)
            if not source_code:
                return None, None

            exec_globals = {"FastMCP": FastMCP}
            exec(source_code, exec_globals)

            # Prefer a FastMCP instance created by the code itself
            for value in exec_globals.values():
                if isinstance(value, FastMCP):
                    return value, None

            # Otherwise, register discovered callables on a new FastMCP
            dynamic = FastMCP(name=f"DynamicServer_{server_id}", stateless_http=True)
            for name, value in exec_globals.items():
                if callable(value) and not name.startswith("__"):
                    dynamic.tool()(value)
            return None, dynamic
        except Exception as exc:
            print(f"[ServerRegistry] Failed to load server {server_id}: {exc}")
            return None, None

# Global server registry
server_registry = ServerRegistry()

# ---------- Lifespan to run session managers of built-in servers ----------

@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(echo_mcp.session_manager.run())
        await stack.enter_async_context(math_mcp.session_manager.run())
        try:
            yield
        finally:
            # Shutdown all dynamic servers
            await server_registry.shutdown_all()


# ---------- ASGI proxy mounted at /server that parses {id} from the path ----------

class DynamicServerProxy:
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            resp = JSONResponse({"error": "Unsupported scope type"}, status_code=500)
            await resp(scope, receive, send)
            return

        # We are mounted at /server; extract "{id}" from the remaining path
        # e.g., path might be "/abc123" or "/abc123/..."
        path = scope.get("path", "") or ""
        # When mounted, Starlette sets 'root_path' to the mount prefix and 'path' to the remainder.
        # So here path should begin with "/" then the id.
        remainder = path.lstrip("/")
        print("remainder:", remainder)
        server_id = remainder.split("/")[2] if remainder else ""
        print(f"[DynamicServerProxy] Parsed server_id: '{server_id}' from path: '{path}', remainder: '{remainder}'")

        if not server_id:
            resp = JSONResponse({"error": "Server ID is required as /server/{id}"}, status_code=400)
            await resp(scope, receive, send)
            return

        # Use server registry to get initialized server
        mcp_server = await server_registry.get_server(server_id)
        if mcp_server is None:
            resp = JSONResponse({"error": "Server not found or failed to load"}, status_code=404)
            await resp(scope, receive, send)
            return

        print(f"[DynamicServerProxy] Using cached MCP server: {mcp_server.name}")
        
        # Strip the prefix path (/test/server/{id}) before delegating to MCP server
        # Find the position after the server ID in the path
        parts = remainder.split("/", 3)  # ['test', 'server', 'id', 'remaining_path']
        if len(parts) > 3:
            mcp_path = "/" + parts[3]  # Get the remaining path after server ID
        else:
            mcp_path = "/"  # Default to root if no remaining path
        
        # Create modified scope with the stripped path
        modified_scope = scope.copy()
        modified_scope["path"] = mcp_path
        modified_scope["raw_path"] = mcp_path.encode()
        
        print(f"[DynamicServerProxy] Original path: {path}, Modified path for MCP: {mcp_path}")
        
        # Delegate to the MCP server's ASGI app with modified scope
        asgi_app = mcp_server.streamable_http_app()
        print(f"[DynamicServerProxy] Delegating to ASGI APP: {asgi_app}")
        await asgi_app(modified_scope, receive, send)


# ---------- Misc sample handler ----------

async def chat_handler(request: Request):
    return JSONResponse({"status": "hello world"})


# ---------- Routes & App ----------

routes = [
    Mount("/echo", echo_mcp.streamable_http_app()),
    Mount("/math", math_mcp.streamable_http_app()),
    Route("/sample", chat_handler, methods=["GET"]),

    # Mount the ASGI proxy at /server. It handles /server/{id} by parsing scope["path"].
    Mount("/server", app=DynamicServerProxy()),
]

router = Router(routes)
app = Starlette(routes=[Mount("/", router)], lifespan=lifespan)
