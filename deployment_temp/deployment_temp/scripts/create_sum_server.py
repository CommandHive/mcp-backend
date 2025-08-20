#!/usr/bin/env python3
"""
Create a minimal MCP server record with a single sum tool.
Usage:
    python scripts/create_sum_server.py

It inserts a new row into the `servers` table with source code that defines
an MCP server instance and exposes a `sum` tool as requested.
"""

import uuid
from datetime import datetime
from services.supabase_client import supabase_client

# NOTE: Update this to the appropriate wallet address or user id if needed

# Minimal FastMCP server code including a sum(a, b) tool
SERVER_CODE = '''
from mcp.server.fastmcp import FastMCP
sum_mcp = FastMCP(name="SumServer", stateless_http=True)

@sum_mcp.tool()
def sum(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b
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
        "Sum Server",
        "sum",
        "Server exposing a single sum(a, b) MCP tool",
        "1.0.0",
        "active",
        "public",
        SERVER_CODE,
        now,
        now,
        "math",
    )

    supabase_client.execute_query(insert_query, values)
    print(f"✅ Created Sum Server. id={server_id} slug=sum")
    print("You can set this environment variable to wire it into /test/sum:")
    print(f"  export TEST_SUM_SERVER_ID={server_id}")


if __name__ == "__main__":
    main()
