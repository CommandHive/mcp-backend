#!/usr/bin/env python3
"""
Combined API Flow Test Runner

This script tests the complete API flow:
1. Authentication endpoints (auth.py)
2. Chat endpoints (chat.py)
3. Uses auth token from step 1 in step 2 to test the full flow

Run this script to test the entire API flow end-to-end.
"""

import sys
import time
from test_auth_flow import run_auth_flow_tests
from test_chat_flow import run_chat_flow_tests

def main():
    print("🎯 MCP Platform API Flow Tests")
    print("=" * 60)
    print("Testing complete API flow: Auth → Chat")
    print("=" * 60)
    
    # Step 1: Run Auth Flow Tests
    print("\n🔐 PHASE 1: Authentication Flow Tests")
    print("-" * 40)
    
    jwt_token = run_auth_flow_tests()
    
    if not jwt_token:
        print("\n❌ Auth tests failed to provide valid JWT token")
        print("   Cannot proceed with chat tests")
        return False
    
    print(f"\n✅ Auth tests completed successfully!")
    print(f"   JWT Token obtained: {jwt_token[:30]}...")
    
    # Short delay between test phases
    print("\n⏳ Waiting 2 seconds before starting chat tests...")
    time.sleep(2)
    
    # Step 2: Run Chat Flow Tests using JWT token from auth
    print("\n💬 PHASE 2: Chat Flow Tests")
    print("-" * 40)
    
    chat_results = run_chat_flow_tests(jwt_token)
    
    # Final Summary
    print("\n" + "=" * 60)
    print("🏁 FINAL TEST SUMMARY")
    print("=" * 60)
    
    if chat_results and chat_results.get("all_passed"):
        print("✅ ALL TESTS PASSED!")
        print("   The API flow is working correctly")
        
        if chat_results.get("chat_session_id"):
            print(f"   Created chat session: {chat_results['chat_session_id']}")
        
        if chat_results.get("sessions"):
            print(f"   Total user sessions: {len(chat_results['sessions'])}")
            
        return True
    else:
        print("⚠️  Some tests failed or had issues")
        print("   Check the detailed output above for specific failures")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)