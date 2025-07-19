#!/usr/bin/env python3
"""
Script to create MCP servers from test.py in the database
Usage: python create_test_servers.py
"""

import uuid
import json
from datetime import datetime
from services.supabase_client import supabase_client

# User wallet address
WALLET_ADDRESS = "0x293d3a1d4261570bf30f0670cd41b5200dc0a08f"

# Echo Server Source Code
echo_server_code = '''
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
'''

# Math Server Source Code
math_server_code = '''
math_mcp = FastMCP(name="MathServer", stateless_http=True)


@math_mcp.tool()
def add_two(n: int) -> int:
    """Tool to add two to the input"""
    return n + 2
'''

def create_server(name, slug, description, source_code, category="utility"):
    """Create a server in the database"""
    try:
        server_id = str(uuid.uuid4())
        now = datetime.now()
        
        query = """
            INSERT INTO servers (
                id, wallet_address, name, slug, description, version, status, 
                visibility, source_code, created_at, updated_at, category
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            server_id,
            WALLET_ADDRESS,
            name,
            slug,
            description,
            "1.0.0",
            "active",
            "public",
            source_code,
            now,
            now,
            category
        )
        
        supabase_client.execute_query(query, values)
        print(f"✅ Created server: {name} (slug: {slug})")
        return server_id
        
    except Exception as e:
        print(f"❌ Error creating server {name}: {e}")
        return None

def create_server_tools(server_id, tools):
    """Create tools for a server"""
    try:
        for tool in tools:
            tool_id = str(uuid.uuid4())
            query = """
                INSERT INTO server_tools (
                    id, server_id, name, description, schema, is_active, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                tool_id,
                server_id,
                tool['name'],
                tool['description'],
                json.dumps(tool.get('schema', {})),
                True,
                datetime.now()
            )
            
            supabase_client.execute_query(query, values)
            print(f"  ✅ Created tool: {tool['name']}")
            
    except Exception as e:
        print(f"❌ Error creating tools for server {server_id}: {e}")

def main():
    """Main function to create test servers"""
    print("🚀 Creating MCP servers from test.py...")
    print(f"👤 User: {WALLET_ADDRESS}")
    print()
    
    # Create Echo Server
    echo_tools = [
        {
            "name": "add",
            "description": "Add two numbers",
            "schema": {
                "type": "function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer", "description": "First number"},
                        "b": {"type": "integer", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            }
        }
    ]
    
    echo_server_id = create_server(
        name="Echo Server",
        slug="echo",
        description="A versatile MCP server with math tools, greeting resources, and prompt generation",
        source_code=echo_server_code,
        category="demo"
    )
    
    if echo_server_id:
        create_server_tools(echo_server_id, echo_tools)
    
    print()
    
    # Create Math Server
    math_tools = [
        {
            "name": "add_two",
            "description": "Tool to add two to the input",
            "schema": {
                "type": "function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "n": {"type": "integer", "description": "Input number"}
                    },
                    "required": ["n"]
                }
            }
        }
    ]
    
    math_server_id = create_server(
        name="Math Server",
        slug="math",
        description="Simple math operations MCP server with add_two functionality",
        source_code=math_server_code,
        category="math"
    )
    
    if math_server_id:
        create_server_tools(math_server_id, math_tools)
    
    print()
    print("🎉 All servers created successfully!")
    print()
    print("📋 You can now access:")
    print("  • Echo Server: /echo")
    print("  • Math Server: /math")
    print()
    print("🔧 Test endpoints:")
    print("  • GET /echo/tools/list")
    print("  • POST /echo/tools/call")
    print("  • GET /math/tools/list")
    print("  • POST /math/tools/call")

if __name__ == "__main__":
    main()