import requests
import json
import time
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8000"

def test_chat_status():
    """Test the chat status endpoint"""
    print("🔍 Testing chat status...")
    
    response = requests.get(f"{BASE_URL}/chat/status")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.status_code == 200

def test_create_chat(jwt_token: str, prompt: str = "Create a simple MCP server that returns hello world"):
    """Test creating a new chat session"""
    print("\n💬 Testing create chat...")
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/create",
        headers=headers,
        data=json.dumps(payload)
    )
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {json.dumps(response_data, indent=2)}")
    
    chat_session_id = None
    if response.status_code == 200 and response_data.get("success"):
        chat_session_id = response_data.get("chat_session_id")
        print(f"Chat Session ID: {chat_session_id}")
        
        # Show generated code if available
        if response_data.get("code"):
            print(f"Generated Code Preview: {response_data.get('code')[:200]}...")
        
        # Show tools if available
        if response_data.get("tools"):
            print(f"Available Tools: {[tool['name'] for tool in response_data.get('tools', [])]}")
    
    return response.status_code == 200, chat_session_id, response_data

def test_continue_chat(jwt_token: str, chat_session_id: str, prompt: str = "Add a function to get the current time"):
    """Test continuing an existing chat session"""
    print(f"\n💬 Testing continue chat (Session: {chat_session_id})...")
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt,
        "chat_id": chat_session_id
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/create",
        headers=headers,
        data=json.dumps(payload)
    )
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {json.dumps(response_data, indent=2)}")
    
    return response.status_code == 200, response_data

def test_get_user_sessions(jwt_token: str):
    """Test getting all user chat sessions"""
    print("\n📝 Testing get user sessions...")
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}/chat/sessions", headers=headers)
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {json.dumps(response_data, indent=2)}")
    
    sessions = []
    if response.status_code == 200 and response_data.get("success"):
        sessions = response_data.get("sessions", [])
        print(f"Found {len(sessions)} sessions")
    
    return response.status_code == 200, sessions

def test_get_session_messages(jwt_token: str, session_id: str):
    """Test getting messages for a specific session"""
    print(f"\n📋 Testing get session messages (Session: {session_id})...")
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{BASE_URL}/chat/sessions/{session_id}/messages", headers=headers)
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {json.dumps(response_data, indent=2)}")
    
    messages = []
    if response.status_code == 200 and response_data.get("success"):
        messages = response_data.get("messages", [])
        print(f"Found {len(messages)} messages")
    
    return response.status_code == 200, messages

def test_execute_tool(jwt_token: str, chat_id: str, tool_name: str, parameters: Dict[str, Any] = None):
    """Test executing a tool from chat generated code"""
    print(f"\n🔧 Testing execute tool '{tool_name}' (Chat: {chat_id})...")
    
    if parameters is None:
        parameters = {}
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "parameters": parameters
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/{chat_id}/tools/{tool_name}/execute",
        headers=headers,
        data=json.dumps(payload)
    )
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {json.dumps(response_data, indent=2)}")
    
    return response.status_code == 200, response_data

def test_deploy_chat_server(jwt_token: str, chat_id: str):
    """Test deploying MCP server from chat session"""
    print(f"\n🚀 Testing deploy chat server (Chat: {chat_id})...")
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    payload = {}
    
    response = requests.post(
        f"{BASE_URL}/chat/{chat_id}/deploy",
        headers=headers,
        data=json.dumps(payload)
    )
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {json.dumps(response_data, indent=2)}")
    
    return response.status_code in [200, 201], response_data

def run_chat_flow_tests(jwt_token: str):
    """Run all chat flow tests using the provided JWT token"""
    print("🚀 Starting Chat API Flow Tests")
    print("=" * 50)
    
    if not jwt_token:
        print("❌ No JWT token provided. Please run auth tests first.")
        return
    
    # Test 1: Chat Status
    status_ok = test_chat_status()
    
    # Test 2: Create New Chat Session
    create_chat_ok, chat_session_id, create_response = test_create_chat(
        jwt_token, 
        "Create a simple MCP server with a hello_world function that returns 'Hello, World!'"
    )
    
    # Test 3: Continue Chat (if first chat was successful)
    continue_chat_ok = False
    if create_chat_ok and chat_session_id:
        continue_chat_ok, continue_response = test_continue_chat(
            jwt_token, 
            chat_session_id, 
            "Add a function to get the current timestamp"
        )
    
    # Test 4: Get User Sessions
    sessions_ok, sessions = test_get_user_sessions(jwt_token)
    
    # Test 5: Get Session Messages (using the first available session)
    messages_ok = False
    messages = []
    session_to_use = chat_session_id if chat_session_id else (sessions[0]["id"] if sessions else None)
    
    if session_to_use:
        messages_ok, messages = test_get_session_messages(jwt_token, session_to_use)
    
    # Test 6: Execute Tool (if available from the chat response)
    tool_execution_ok = False
    if create_chat_ok and create_response.get("tools"):
        available_tools = create_response.get("tools", [])
        if available_tools:
            first_tool = available_tools[0]
            tool_name = first_tool["name"]
            print(f"\n🔧 Found tool: {tool_name}")
            tool_execution_ok, tool_response = test_execute_tool(jwt_token, chat_session_id, tool_name)
    
    # Test 7: Deploy Chat Server (if the chat has deployable code)
    deploy_ok = False
    if create_chat_ok and chat_session_id and create_response.get("is_deployable"):
        deploy_ok, deploy_response = test_deploy_chat_server(jwt_token, chat_session_id)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Chat Flow Test Summary:")
    print(f"✅ Chat Status: {'PASS' if status_ok else 'FAIL'}")
    print(f"💬 Create Chat: {'PASS' if create_chat_ok else 'FAIL'}")
    print(f"💬 Continue Chat: {'PASS' if continue_chat_ok else 'FAIL (skipped if create failed)'}")
    print(f"📝 Get Sessions: {'PASS' if sessions_ok else 'FAIL'}")
    print(f"📋 Get Messages: {'PASS' if messages_ok else 'FAIL (skipped if no sessions)'}")
    print(f"🔧 Execute Tool: {'PASS' if tool_execution_ok else 'FAIL (skipped if no tools available)'}")
    print(f"🚀 Deploy Server: {'PASS' if deploy_ok else 'FAIL (skipped if not deployable)'}")
    
    return {
        "chat_session_id": chat_session_id,
        "sessions": sessions,
        "messages": messages,
        "all_passed": all([status_ok, create_chat_ok, sessions_ok])
    }

if __name__ == "__main__":
    # This script expects a JWT token to be passed
    import sys
    
    if len(sys.argv) > 1:
        jwt_token = sys.argv[1]
        run_chat_flow_tests(jwt_token)
    else:
        print("❌ Please provide a JWT token as argument")
        print("Usage: python test_chat_flow.py <JWT_TOKEN>")

 """
💬 PHASE 2: Chat Flow Tests
----------------------------------------
🚀 Starting Chat API Flow Tests
==================================================
🔍 Testing chat status...
Status: 200
Response: {'status': 'MCP Chat API'}

💬 Testing create chat...
Status: 200
Response: {
  "chat_session_id": "4005f2e6-8577-4b11-9ae1-e9e476de2989",
  "code": "from mcp.server.fastmcp import FastMCP\n\nhello_world_mcp = FastMCP(name=\"HelloWorldServer\", stateless_http=True)\n\n@hello_world_mcp.tool()\ndef hello_world() -> str:\n    \"\"\"Return a simple 'Hello, World!' greeting.\"\"\"\n    return \"Hello, World!\"",
  "next_steps": "Congratulations! Your Hello World MCP server is complete and ready to deploy. This simple server provides a hello_world function that returns \"Hello, World!\" when called. You can now deploy this server and connect it to any MCP-compatible AI assistant.",
  "is_deployable": true,
  "tools": [
    {
      "instance": "hello_world_mcp",
      "name": "hello_world",
      "description": "Return a simple 'Hello, World!' greeting.",
      "parameters": {
        "properties": {},
        "title": "hello_worldArguments",
        "type": "object"
      },
      "is_async": false,
      "output_schema": {
        "properties": {
          "result": {
            "title": "Result",
            "type": "string"
          }
        },
        "required": [
          "result"
        ],
        "title": "hello_worldOutput",
        "type": "object"
      }
    }
  ],
  "inference_id": null,
  "episode_id": null,
  "usage": {
    "prompt_tokens": 732,
    "completion_tokens": 174,
    "total_tokens": 906
  },
  "success": true
}
Chat Session ID: 4005f2e6-8577-4b11-9ae1-e9e476de2989
Generated Code Preview: from mcp.server.fastmcp import FastMCP

hello_world_mcp = FastMCP(name="HelloWorldServer", stateless_http=True)

@hello_world_mcp.tool()
def hello_world() -> str:
    "Return a simple 'Hello, World!...
Available Tools: ['hello_world']

💬 Testing continue chat (Session: 4005f2e6-8577-4b11-9ae1-e9e476de2989)...
Status: 200
Response: {
  "chat_session_id": "4005f2e6-8577-4b11-9ae1-e9e476de2989",
  "code": "from mcp.server.fastmcp import FastMCP\nfrom datetime import datetime\n\nhello_world_mcp = FastMCP(name=\"HelloWorldServer\", stateless_http=True)\n\n@hello_world_mcp.tool()\ndef hello_world() -> str:\n    \"\"\"Return a simple 'Hello, World!' greeting.\"\"\"\n    return \"Hello, World!\"\n\n@hello_world_mcp.tool()\ndef get_current_timestamp() -> str:\n    \"\"\"Get the current timestamp in ISO 8601 format.\"\"\"\n    return datetime.now().isoformat()",
  "next_steps": "Perfect! I've added a `get_current_timestamp()` function to your MCP server. This function returns the current date and time in ISO 8601 format. Your server now has two tools:\n1. `hello_world()` - Returns \"Hello, World!\"\n2. `get_current_timestamp()` - Returns the current timestamp\n\nThe server is still complete and ready to deploy!",
  "is_deployable": true,
  "tools": [
    {
      "instance": "hello_world_mcp",
      "name": "hello_world",
      "description": "Return a simple 'Hello, World!' greeting.",
      "parameters": {
        "properties": {},
        "title": "hello_worldArguments",
        "type": "object"
      },
      "is_async": false,
      "output_schema": {
        "properties": {
          "result": {
            "title": "Result",
            "type": "string"
          }
        },
        "required": [
          "result"
        ],
        "title": "hello_worldOutput",
        "type": "object"
      }
    },
    {
      "instance": "hello_world_mcp",
      "name": "get_current_timestamp",
      "description": "Get the current timestamp in ISO 8601 format.",
      "parameters": {
        "properties": {},
        "title": "get_current_timestampArguments",
        "type": "object"
      },
      "is_async": false,
      "output_schema": {
        "properties": {
          "result": {
            "title": "Result",
            "type": "string"
          }
        },
        "required": [
          "result"
        ],
        "title": "get_current_timestampOutput",
        "type": "object"
      }
    }
  ],
  "inference_id": null,
  "episode_id": null,
  "usage": {
    "prompt_tokens": 445,
    "completion_tokens": 258,
    "total_tokens": 703
  },
  "success": true
}

📝 Testing get user sessions...
Status: 200
Response: {
  "success": true,
  "sessions": [
    {
      "id": "4005f2e6-8577-4b11-9ae1-e9e476de2989",
      "title": "MCP Server Chat",
      "created_at": "2025-08-11T08:53:07.023704+00:00",
      "updated_at": "2025-08-11T08:53:12.965593+00:00"
    },
    {
      "id": "94401584-6e30-4695-a9d1-7d883aa5119e",
      "title": "MCP Server Chat",
      "created_at": "2025-08-11T03:55:46.442410+00:00",
      "updated_at": "2025-08-11T03:55:52.260958+00:00"
    }
  ],
  "total": 2
}
Found 2 sessions

📋 Testing get session messages (Session: 4005f2e6-8577-4b11-9ae1-e9e476de2989)...
Status: 200
Response: {
  "success": true,
  "session_id": "4005f2e6-8577-4b11-9ae1-e9e476de2989",
  "messages": [
    {
      "id": "56ffcd66-d62c-4ed5-99ae-880bb4b2dc7d",
      "session_id": "4005f2e6-8577-4b11-9ae1-e9e476de2989",
      "role": "user",
      "code": null,
      "next_steps": null,
      "is_deployable": null,
      "content": "Create a simple MCP server with a hello_world function that returns 'Hello, World!'",
      "metadata": null,
      "created_at": "2025-08-11T08:53:07.031089+00:00"
    },
    {
      "id": "f85d65b3-91b1-4378-8c40-cc8033bfeb38",
      "session_id": "4005f2e6-8577-4b11-9ae1-e9e476de2989",
      "role": "assistant",
      "code": "from mcp.server.fastmcp import FastMCP\n\nhello_world_mcp = FastMCP(name=\"HelloWorldServer\", stateless_http=True)\n\n@hello_world_mcp.tool()\ndef hello_world() -> str:\n    \"\"\"Return a simple 'Hello, World!' greeting.\"\"\"\n    return \"Hello, World!\"",
      "next_steps": "Congratulations! Your Hello World MCP server is complete and ready to deploy. This simple server provides a hello_world function that returns \"Hello, World!\" when called. You can now deploy this server and connect it to any MCP-compatible AI assistant.",
      "is_deployable": true,
      "content": "{\"code\": \"from mcp.server.fastmcp import FastMCP\\n\\nhello_world_mcp = FastMCP(name=\\\"HelloWorldServer\\\", stateless_http=True)\\n\\n@hello_world_mcp.tool()\\ndef hello_world() -> str:\\n    \\\"\\\"\\\"Return a simple 'Hello, World!' greeting.\\\"\\\"\\\"\\n    return \\\"Hello, World!\\\"\", \"next_steps\": \"Congratulations! Your Hello World MCP server is complete and ready to deploy. This simple server provides a hello_world function that returns \\\"Hello, World!\\\" when called. You can now deploy this server and connect it to any MCP-compatible AI assistant.\", \"is_deployable\": true}",
      "metadata": null,
      "created_at": "2025-08-11T08:53:12.957929+00:00"
    },
    {
      "id": "8aeece5c-a791-481f-b35c-f283ede8c967",
      "session_id": "4005f2e6-8577-4b11-9ae1-e9e476de2989",
      "role": "user",
      "code": null,
      "next_steps": null,
      "is_deployable": null,
      "content": "Add a function to get the current timestamp",
      "metadata": null,
      "created_at": "2025-08-11T08:53:12.970176+00:00"
    },
    {
      "id": "964ba0c6-d6f6-4ce7-b010-3274d2423b23",
      "session_id": "4005f2e6-8577-4b11-9ae1-e9e476de2989",
      "role": "assistant",
      "code": "from mcp.server.fastmcp import FastMCP\nfrom datetime import datetime\n\nhello_world_mcp = FastMCP(name=\"HelloWorldServer\", stateless_http=True)\n\n@hello_world_mcp.tool()\ndef hello_world() -> str:\n    \"\"\"Return a simple 'Hello, World!' greeting.\"\"\"\n    return \"Hello, World!\"\n\n@hello_world_mcp.tool()\ndef get_current_timestamp() -> str:\n    \"\"\"Get the current timestamp in ISO 8601 format.\"\"\"\n    return datetime.now().isoformat()",
      "next_steps": "Perfect! I've added a `get_current_timestamp()` function to your MCP server. This function returns the current date and time in ISO 8601 format. Your server now has two tools:\n1. `hello_world()` - Returns \"Hello, World!\"\n2. `get_current_timestamp()` - Returns the current timestamp\n\nThe server is still complete and ready to deploy!",
      "is_deployable": true,
      "content": "{\"code\": \"from mcp.server.fastmcp import FastMCP\\nfrom datetime import datetime\\n\\nhello_world_mcp = FastMCP(name=\\\"HelloWorldServer\\\", stateless_http=True)\\n\\n@hello_world_mcp.tool()\\ndef hello_world() -> str:\\n    \\\"\\\"\\\"Return a simple 'Hello, World!' greeting.\\\"\\\"\\\"\\n    return \\\"Hello, World!\\\"\\n\\n@hello_world_mcp.tool()\\ndef get_current_timestamp() -> str:\\n    \\\"\\\"\\\"Get the current timestamp in ISO 8601 format.\\\"\\\"\\\"\\n    return datetime.now().isoformat()\", \"next_steps\": \"Perfect! I've added a `get_current_timestamp()` function to your MCP server. This function returns the current date and time in ISO 8601 format. Your server now has two tools:\\n1. `hello_world()` - Returns \\\"Hello, World!\\\"\\n2. `get_current_timestamp()` - Returns the current timestamp\\n\\nThe server is still complete and ready to deploy!\", \"is_deployable\": true}",
      "metadata": null,
      "created_at": "2025-08-11T08:53:19.621345+00:00"
    }
  ],
  "total": 4
}
Found 4 messages

🔧 Found tool: hello_world

🔧 Testing execute tool 'hello_world' (Chat: 4005f2e6-8577-4b11-9ae1-e9e476de2989)...
Status: 200
Response: {
  "success": true,
  "result": "Hello, World!",
  "tool_name": "hello_world",
  "parameters": {}
}

🚀 Testing deploy chat server (Chat: 4005f2e6-8577-4b11-9ae1-e9e476de2989)...
Status: 201
Response: {
  "success": true,
  "message": "MCP server deployed successfully",
  "server": {
    "id": "fe1e3a32-304d-441d-b196-2b386720f6a5",
    "name": "Hello World Server",
    "slug": "hello-world-server-1",
    "description": "A simple demonstration MCP server that provides basic greeting and timestamp functionality. It offers tools to return a \"Hello, World!\" message and get the current timestamp in ISO 8601 format.",
    "version": "1.0.0",
    "status": "active",
    "visibility": "private",
    "category": "chat-generated",
    "tags": null,
    "created_at": "2025-08-11T08:53:19.637626+00:00"
  },
  "chat_id": "4005f2e6-8577-4b11-9ae1-e9e476de2989"
}

==================================================
📊 Chat Flow Test Summary:
✅ Chat Status: PASS
💬 Create Chat: PASS
💬 Continue Chat: PASS
📝 Get Sessions: PASS
📋 Get Messages: PASS
🔧 Execute Tool: PASS
🚀 Deploy Server: PASS

============================================================
🏁 FINAL TEST SUMMARY
============================================================
✅ ALL TESTS PASSED!
   The API flow is working correctly
   Created chat session: 4005f2e6-8577-4b11-9ae1-e9e476de2989
   Total user sessions: 2
    """