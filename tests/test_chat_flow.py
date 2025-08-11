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