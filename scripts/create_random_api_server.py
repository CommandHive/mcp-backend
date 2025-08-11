#!/usr/bin/env python3
"""
Create a minimal MCP server record that pings a random API.
Usage:
    python scripts/create_random_api_server.py

It inserts a new row into the `servers` table with source code that defines
an MCP server instance and exposes a `ping_random_api` tool.
"""

import uuid
from datetime import datetime
from services.supabase_client import supabase_client

# MCP server code that pings a random API
SERVER_CODE = '''
import requests
import random

random_api_mcp = FastMCP(name="RandomAPIServer", stateless_http=True)

@random_api_mcp.tool()
def ping_random_api() -> str:
    """Ping a random API and return the results."""
    apis = [
        "https://jsonplaceholder.typicode.com/posts/1",
        "https://httpbin.org/json",
        "https://api.github.com/zen",
        "https://httpbin.org/uuid",
        "https://jsonplaceholder.typicode.com/users/1"
    ]
    
    selected_api = random.choice(apis)
    
    try:
        response = requests.get(selected_api, timeout=10)
        response.raise_for_status()
        
        return f"API: {selected_api}\\nStatus: {response.status_code}\\nResponse: {response.text[:500]}"
    except requests.exceptions.RequestException as e:
        return f"Error pinging {selected_api}: {str(e)}"
'''


def main() -> None:
    server_id = str(uuid.uuid4())
    now = datetime.now()

    insert_query = """
        INSERT INTO servers (
            id, user_id, name, slug, description, version,
            status, visibility, source_code, created_at, updated_at, category
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        )
    """

    values = (
        server_id,
        "ab850c4a-d376-4d53-bf35-ff2d2ea2e191",
        "Random API Server",
        "random-api",
        "Server that pings random APIs and returns results",
        "1.0.0",
        "active",
        "public",
        SERVER_CODE,
        now,
        now,
        "utility",
    )

    supabase_client.execute_query(insert_query, values)
    print(f"✅ Created Random API Server. id={server_id} slug=random-api")
    print("You can set this environment variable to wire it into tests:")
    print(f"  export RANDOM_API_SERVER_ID={server_id}")


if __name__ == "__main__":
    main()