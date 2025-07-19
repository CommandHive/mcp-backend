"""
Run from the repository root:
    uvicorn examples.snippets.servers.streamable_starlette_mount:app --reload
"""

import contextlib

from starlette.applications import Starlette
from starlette.routing import Route, Router, Mount
from starlette.responses import JSONResponse

from mcp.server.fastmcp import FastMCP

# Create the Echo server
echo_mcp = FastMCP(name="EchoServer", stateless_http=True)


@echo_mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@echo_mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# Add a prompt
@echo_mcp.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."



# Create the Math server
math_mcp = FastMCP(name="MathServer", stateless_http=True)


@math_mcp.tool()
def add_two(n: int) -> int:
    """Tool to add two to the input"""
    return n + 2


# Create a combined lifespan to manage both session managers
@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(echo_mcp.session_manager.run())
        await stack.enter_async_context(math_mcp.session_manager.run())
        yield


async def chat_handler(request):
    return JSONResponse({"status": "hello world"})


router = Router([
    Mount("/echo", echo_mcp.streamable_http_app()),
    Mount("/math", math_mcp.streamable_http_app()),
    Route("/sample", chat_handler, methods=["GET"])
])