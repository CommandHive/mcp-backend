#!/usr/bin/env python3
"""
Create a minimal MCP server record with a single subtraction tool.
Usage:
    python scripts/create_subtraction_server.py

It inserts a new row into the `servers` table with source code that defines
an MCP server instance and exposes a `subtract` tool.
"""

import uuid
from datetime import datetime
from services.supabase_client import supabase_client

# MCP server code including a subtract(a, b) tool
SERVER_CODE = '''
subtraction_mcp = FastMCP(name="SubtractionServer", stateless_http=True)

@subtraction_mcp.tool()
def subtract(a: int, b: int) -> int:
    """Return the difference between two integers (a - b)."""
    return a - b
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
        "Subtraction Server",
        "subtraction",
        "Server exposing a single subtract(a, b) MCP tool",
        "1.0.0",
        "active",
        "public",
        SERVER_CODE,
        now,
        now,
        "math",
    )

    supabase_client.execute_query(insert_query, values)
    print(f"✅ Created Subtraction Server. id={server_id} slug=subtraction")
    print("You can set this environment variable to wire it into tests:")
    print(f"  export SUBTRACTION_SERVER_ID={server_id}")


if __name__ == "__main__":
    main()