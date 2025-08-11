import requests
import json
import time
from typing import Optional

BASE_URL = "http://localhost:8000"

def test_auth_status():
    """Test the auth status endpoint"""
    print("🔍 Testing auth status...")
    
    response = requests.get(f"{BASE_URL}/auth/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.status_code == 200


def test_create_session_email():
    """Test creating session with email provider"""
    print("\n👤 Testing create session (email provider)...")
    
    payload = {
        "email": "test@example.com",
        "name": "Test User",
        "provider": "email",
        "provider_id": "test@example.com"
    }
    
    response = requests.post(
        f"{BASE_URL}/auth/session",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {response_data}")
    
    # Extract JWT token if successful
    jwt_token = None
    if response.status_code == 200 and response_data.get("success"):
        jwt_token = response_data.get("access_token")
        print(f"JWT Token: {jwt_token[:50]}..." if jwt_token else "No token")
    
    return response.status_code == 200, jwt_token

def test_create_session_google():
    """Test creating session with Google provider"""
    print("\n🔍 Testing create session (Google provider)...")
    
    payload = {
        "email": "testgoogle@gmail.com",
        "name": "Google Test User",
        "provider": "google",
        "provider_id": "google_user_id_123",
        "image": "https://lh3.googleusercontent.com/a/profile.jpg"
    }
    
    response = requests.post(
        f"{BASE_URL}/auth/session",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {response_data}")
    
    # Extract JWT token if successful
    jwt_token = None
    if response.status_code == 200 and response_data.get("success"):
        jwt_token = response_data.get("access_token")
        print(f"JWT Token: {jwt_token[:50]}..." if jwt_token else "No token")
    
    return response.status_code == 200, jwt_token

def test_oauth_callback():
    """Test OAuth callback endpoint"""
    print("\n🔗 Testing OAuth callback...")
    
    payload = {
        "provider": "google",
        "user": {
            "id": "google_user_id_456",
            "email": "oauth@gmail.com",
            "name": "OAuth Test User",
            "picture": "https://example.com/avatar.jpg"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/auth/oauth",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {response_data}")
    
    # Extract JWT token if successful
    jwt_token = None
    if response.status_code == 200 and response_data.get("success"):
        jwt_token = response_data.get("access_token")
        print(f"JWT Token: {jwt_token[:50]}..." if jwt_token else "No token")
    
    return response.status_code == 200, jwt_token

def test_get_current_user(jwt_token: str):
    """Test getting current user with JWT token"""
    print("\n👤 Testing get current user...")
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    print(headers)
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    
    print(f"Status: {response.status_code}")
    response_data = response.json()
    print(f"Response: {response_data}")
    
    return response.status_code == 200, response_data

def run_auth_flow_tests():
    """Run all auth flow tests"""
    print("🚀 Starting Auth API Flow Tests")
    print("=" * 50)
    
    # Test 1: Auth Status
    status_ok = test_auth_status()
        
    # Test 3: Create Session with Email Provider
    email_session_ok, email_jwt = test_create_session_email()
    
    
    # Test 6: Get Current User (using one of the JWT tokens)
    current_user_ok = False
    current_user_data = None
    
    # Try with email JWT first, then Google JWT, then OAuth JWT
    for token_name, jwt_token in [("Email", email_jwt)]:
        if jwt_token:
            print(f"\n🔍 Testing get current user with {token_name} JWT...")
            current_user_ok, current_user_data = test_get_current_user(jwt_token)
            if current_user_ok:
                break
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Auth Flow Test Summary:")
    print(f"✅ Auth Status: {'PASS' if status_ok else 'FAIL'}")
    print(f"👤 Email Session: {'PASS' if email_session_ok else 'FAIL'}")
    print(f"👤 Get Current User: {'PASS' if current_user_ok else 'FAIL'}")
    
    # Return the last valid JWT token for use in chat tests
    for jwt_token in [email_jwt]:
        if jwt_token:
            return jwt_token
    
    return None

if __name__ == "__main__":
    jwt_token = run_auth_flow_tests()
    if jwt_token:
        print(f"\n🎯 Valid JWT Token for Chat Tests: {jwt_token[:50]}...")
    else:
        print("\n❌ No valid JWT token obtained for Chat Tests")