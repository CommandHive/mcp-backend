from starlette.routing import Route, Router
from starlette.responses import JSONResponse
from starlette.requests import Request
from datetime import datetime
from models.user import User, NextAuthUserRequest
from services.auth_service import auth_service
from services.user_service import user_service


async def auth_status(request: Request):
    """Auth API status and documentation."""
    return JSONResponse({
        "success": True,
        "message": "CommandHive Next-Auth Integration API",
        "version": "2.0.0",
        "description": "Backend API for Next.js frontend using next-auth",
        "flow": [
            "1. Frontend handles OAuth with next-auth (Google, GitHub, Email)",
            "2. Frontend sends user data to POST /auth/session",
            "3. Backend creates/updates user and returns JWT token",
            "4. Use Bearer token in Authorization header for authenticated requests"
        ],
        "endpoints": {
            "POST /session": "Create/update user session from next-auth data",
            "GET /me": "Get current user info (requires Bearer token)",
            "GET /": "This status endpoint"
        }
    })


async def create_session(request: Request):
    """Create or update user session from next-auth data."""
    try:
        body = await request.json()
        user_request = NextAuthUserRequest(**body)
        
        # Create or update user based on the provider
        if user_request.provider == "email":
            user = await user_service.create_or_update_user_by_email(
                email=user_request.email,
                display_name=user_request.name or user_request.email
            )
        elif user_request.provider == "google":
            user = await user_service.create_or_update_user_oauth(
                email=user_request.email,
                display_name=user_request.name or user_request.email,
                avatar_url=user_request.image,
                google_id=user_request.provider_id
            )
        elif user_request.provider == "github":
            user = await user_service.create_or_update_user_oauth(
                email=user_request.email,
                display_name=user_request.name or user_request.email,
                avatar_url=user_request.image,
                github_id=user_request.provider_id,
                username=user_request.username
            )
        else:
            return JSONResponse(
                {"success": False, "error": "Unsupported provider"},
                status_code=400
            )
        
        # Generate JWT token
        token_data = {
            "sub": user.email,
            "email": user.email,
            "display_name": user.display_name,
            "provider": user_request.provider
        }
        access_token = auth_service.create_access_token(token_data)
        
        return JSONResponse({
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.get_jwt_expiration_seconds(),
            "user": {
                "email": user.email,
                "display_name": user.display_name,
                "username": user.username,
                "avatar_url": user.avatar_url,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "wallet_address": user.wallet_address
            }
        })
        
    except Exception as e:
        print(f"Error in create_session: {e}")
        return JSONResponse(
            {"success": False, "error": "Failed to create session"},
            status_code=500
        )


async def get_current_user(request: Request):
    """Get current authenticated user info."""
    try:
        # Extract and validate token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"success": False, "error": "Missing or invalid authorization header"},
                status_code=401
            )
        
        token = auth_header.split(" ")[1]
        payload = auth_service.verify_token(token)
        
        if not payload:
            return JSONResponse(
                {"success": False, "error": "Invalid or expired token"},
                status_code=401
            )
        
        # Get email from token
        email = payload.get("sub")
        if not email:
            return JSONResponse(
                {"success": False, "error": "Invalid token payload"},
                status_code=401
            )
        
        # Get user from database
        user = await user_service.get_user_by_email(email)
        if not user:
            return JSONResponse(
                {"success": False, "error": "User not found"},
                status_code=404
            )
        
        return JSONResponse({
            "success": True,
            "user": {
                "email": user.email,
                "display_name": user.display_name,
                "username": user.username,
                "avatar_url": user.avatar_url,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "wallet_address": user.wallet_address
            }
        })
        
    except Exception as e:
        print(f"Error in get_current_user: {e}")
        return JSONResponse(
            {"success": False, "error": "Failed to get user"},
            status_code=500
        )


router = Router(routes=[
    Route("/", auth_status, methods=["GET"]),
    Route("/session", create_session, methods=["POST"]),
    Route("/me", get_current_user, methods=["GET"])
])

"""
1. GET /auth/ - Auth Status

  curl -X GET http://localhost:8000/auth/

  2. POST /auth/session - Create Session (Email Provider)

  curl -X POST http://localhost:8000/auth/session \
    -H "Content-Type: application/json" \
    -d '{
      "email": "user@example.com",
      "name": "John Doe",
      "provider": "email",
      "provider_id": "user@example.com"
    }'

  3. POST /auth/session - Create Session (Google Provider)

  curl -X POST http://localhost:8000/auth/session \
    -H "Content-Type: application/json" \
    -d '{
      "email": "user@gmail.com",
      "name": "John Doe",
      "provider": "google",
      "provider_id": "google_user_id_123",
      "image": "https://lh3.googleusercontent.com/a/profile.jpg"
    }'

  4. POST /auth/session - Create Session (GitHub Provider)

  curl -X POST http://localhost:8000/auth/session \
    -H "Content-Type: application/json" \
    -d '{
      "email": "user@example.com",
      "name": "John Doe",
      "provider": "github",
      "provider_id": "github_user_id_123",
      "username": "johndoe",
      "image": "https://avatars.githubusercontent.com/u/123456"
    }'

  5. GET /auth/me - Get Current User (requires Bearer token)

  curl -X GET http://localhost:8000/auth/me \
    -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
"""