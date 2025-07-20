from starlette.routing import Router
from starlette.responses import JSONResponse
import requests
import json


MCP_SERVER_DOCUMENTATION = """
# MCP Server Creation Guide

MCP (Model Context Protocol) servers are Python applications that provide tools and resources to AI assistants.

## Basic Structure

```python
import asyncio
from mcp import Tool
from mcp.server import Server
from mcp.tools import Tool
from typing import Any

app = Server("your-server-name")

@app.tool()
async def your_tool_name(arg1: str, arg2: int = 10) -> str:
    \"\"\"
    Description of what your tool does.
    
    Args:
        arg1: Description of first argument
        arg2: Description of second argument (optional, defaults to 10)
    
    Returns:
        Description of return value
    \"\"\"
    # Your tool implementation here
    return f"Result: {arg1} with {arg2}"

if __name__ == "__main__":
    asyncio.run(app.run())
```

## Key Components

1. **Server**: The main MCP server instance
2. **Tools**: Functions decorated with @app.tool() that the AI can call
3. **Resources**: Data or files the AI can access (use @app.resource())
4. **Prompts**: Pre-defined prompts the AI can use (use @app.prompt())

## Tool Guidelines

- Use clear, descriptive function names
- Include comprehensive docstrings
- Add type hints for all parameters
- Handle errors gracefully
- Return meaningful results

## Example Tools

```python
@app.tool()
async def get_weather(city: str) -> str:
    \"\"\"Get current weather for a city\"\"\"
    # Weather API call implementation
    return f"Weather in {city}: Sunny, 75°F"

@app.tool() 
async def calculate_tip(bill_amount: float, tip_percentage: float = 0.18) -> dict:
    \"\"\"Calculate tip and total for a bill\"\"\"
    tip = bill_amount * tip_percentage
    total = bill_amount + tip
    return {"tip": tip, "total": total, "bill": bill_amount}
```

Always ensure your MCP server follows these patterns for proper integration.
"""


async def generate_mcp_server(request):
    try:
        body = await request.json()
        user_prompt = body.get("prompt", "")
        
        if not user_prompt:
            return JSONResponse(
                {"error": "Prompt is required"}, 
                status_code=400
            )
        
        # Prepare the inference API request
        inference_payload = {
            "function_name": "chat_with_assisstant",
            "input": {
                "system": f"""You are an expert MCP server developer. Your task is to create a complete, working MCP server based on the user's requirements.

{MCP_SERVER_DOCUMENTATION}

Guidelines:
- Generate complete, functional Python code
- Include all necessary imports
- Add proper error handling
- Use descriptive function and variable names
- Include comprehensive docstrings
- Follow the MCP server patterns shown above
- Make the code production-ready

Return ONLY the Python code for the MCP server, no explanations or markdown formatting.""",
                "messages": [
                    {
                        "role": "user", 
                        "content": user_prompt
                    }
                ]
            }
        }
        
        # Make request to inference API
        response = requests.post(
            "https://tensorcloud.commandhive.xyz/api/inference",
            headers={"Content-Type": "application/json"},
            json=inference_payload,
            timeout=30
        )
        
        if response.status_code != 200:
            return JSONResponse(
                {"error": "Failed to generate MCP server"}, 
                status_code=500
            )
        
        result = response.json()
        
        # Extract the generated MCP server code
        mcp_server_code = ""
        if "content" in result and result["content"]:
            for content_item in result["content"]:
                if content_item.get("type") == "text":
                    mcp_server_code += content_item.get("text", "")
        
        return JSONResponse({
            "mcp_server_code": mcp_server_code,
            "inference_id": result.get("inference_id"),
            "episode_id": result.get("episode_id"),
            "usage": result.get("usage"),
            "success": True
        })
        
    except requests.exceptions.RequestException as e:
        return JSONResponse(
            {"error": f"Request failed: {str(e)}"}, 
            status_code=500
        )
    except json.JSONDecodeError:
        return JSONResponse(
            {"error": "Invalid JSON in request body"}, 
            status_code=400
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"Internal server error: {str(e)}"}, 
            status_code=500
        )


async def chat_handler(request):
    return JSONResponse({"status": "MCP Server Generator API"})


router = Router([
    ("/", chat_handler, ["GET"]),
    ("/generate-mcp-server", generate_mcp_server, ["POST"])
])