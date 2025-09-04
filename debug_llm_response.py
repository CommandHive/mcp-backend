#!/usr/bin/env python3
"""
Debug script to test LLM response and parsing
"""

import sys
sys.path.append('.')

from services.llm_service import llm_service

# Test messages
test_messages = [
    {
        "role": "user", 
        "content": "Create a simple MCP server with a hello_world function that returns Hello World"
    }
]

print("Testing LLM response...")
print("=" * 50)

try:
    # Call the LLM service directly
    response = llm_service.chat_with_assistant(
        messages=test_messages,
        chat_session_id="debug-test",
        is_new_session=True,
        provider="bedrock"
    )
    
    print("Raw LLM API response:")
    print("-" * 30)
    print(response)
    print("-" * 30)
    
    # Extract content
    extracted = llm_service.extract_content(response)
    
    print("\nExtracted content:")
    print("-" * 30)
    print(f"Code: {extracted.get('code', 'EMPTY')[:200]}...")
    print(f"Next steps: {extracted.get('next_steps', 'EMPTY')[:100]}...")
    print(f"Is deployable: {extracted.get('is_deployable', 'EMPTY')}")
    print("-" * 30)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()