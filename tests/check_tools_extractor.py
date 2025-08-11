import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.chat import extract_tools_from_code
from mcp.server.fastmcp import FastMCP

def test_extract_tools():
    code = """import datetime
from mcp.server.fastmcp import FastMCP

hello_world_mcp = FastMCP(name="HelloWorldServer", stateless_http=True)

@hello_world_mcp.tool()
def hello_world() -> str:
    \"\"\"Return a simple 'Hello, World!' greeting message.\"\"\"
    return "Hello, World!"

@hello_world_mcp.tool()
def get_current_timestamp() -> str:
    \"\"\"Get the current timestamp in ISO 8601 format.
    
    Returns:
        str: Current timestamp in ISO 8601 format (YYYY-MM-DDTHH:MM:SS.ssssss)
    \"\"\"
    return datetime.datetime.now().isoformat()"""

    print("Testing extract_tools_from_code with sample FastMCP code...")
    print("=" * 60)
    
    tools = extract_tools_from_code(code, "test_session_123")
    
    print("=" * 60)
    print(f"Extracted {len(tools)} tools:")
    
    for tool in tools:
        print(f"\nTool: {tool['name']}")
        print(f"  Description: {tool['description']}")
        print(f"  Instance: {tool['instance']}")
        print(f"  Parameters: {tool['parameters']}")
        print(f"  Is Async: {tool['is_async']}")
        print(f"  Output Schema: {tool['output_schema']}")

if __name__ == "__main__":
    test_extract_tools()