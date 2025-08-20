from starlette.routing import Route, Router
from starlette.responses import JSONResponse
from starlette.requests import Request
from datetime import datetime
from models.user import User, NextAuthUserRequest, EmailAuthRequest, MagicLinkRequest, MagicLinkVerifyRequest
from services.auth_service import auth_service
from services.user_service import user_service
from services.magic_link_service import magic_link_service
from services.supabase_client import supabase_client



async def get_current_user(request: Request):
    """Get current authenticated user info from NextAuth session."""
    try:
        # User data is already validated by NextAuthMiddleware and stored in request.state
        if hasattr(request.state, 'user') and request.state.user:
            user_data = request.state.user
            
            response_data = {
                "success": True,
                "user": {
                    "id": user_data["id"],
                    "email": user_data["email"],
                    "display_name": user_data["display_name"],
                    "username": user_data["username"],
                    "avatar_url": user_data["avatar_url"],
                    "subscription_tier": user_data["subscription_tier"],
                    "is_active": user_data["is_active"],
                    "wallet_address": user_data["wallet_address"],
                    "user_id": user_data["id"]
                }
            }
                        
            return JSONResponse(response_data)
        else:
            return JSONResponse(
                {"success": False, "error": "User not authenticated"},
                status_code=401
            )
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": "Failed to get user"},
            status_code=500
        )


async def create_session(request: Request):
    """Create or update user session from next-auth data (backward compatibility)."""
    try:
        body = await request.json()
        user_request = NextAuthUserRequest(**body)
        
        # Create or update user based on the provider
        if user_request.provider == "email":
            user = await user_service.create_or_update_user_by_email(
                email=user_request.email,
                display_name=user_request.name or user_request.email
            )
        elif user_request.provider == "google" or user_request.provider == "nextauth":
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
        
        response_data = {
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
                "wallet_address": user.wallet_address,
                "user_id": user.id
            }
        }
        
        return JSONResponse(response_data)
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": "Failed to create session"},
            status_code=500
        )


async def auth_status(request: Request):
    """Get authentication status."""
    return JSONResponse({"success": True, "message": "Auth service is running"})


async def send_magic_link(request: Request):
    """Send magic link to user's email for passwordless authentication."""
    try:
        body = await request.json()
        magic_request = MagicLinkRequest(**body)
        
        
        # Send magic link
        result = await magic_link_service.send_magic_link(
            email=magic_request.email,
            display_name=magic_request.display_name
        )
        
        return JSONResponse(result)
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": "Failed to send magic link"},
            status_code=500
        )


async def verify_magic_link(request: Request):
    """Verify magic link token and return JWT."""
    try:
        body = await request.json()
        verify_request = MagicLinkVerifyRequest(**body)
        
        
        # Verify magic link token
        result = await magic_link_service.verify_magic_token(verify_request.token)
        
        if result["success"]:
            return JSONResponse(result)
        else:
            return JSONResponse(result, status_code=401)
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": "Failed to verify magic link"},
            status_code=500
        )


async def github_oauth_callback(request: Request):
    """Handle GitHub OAuth callback with authorization code."""
    try:
        body = await request.json()
        code = body.get("code")
        state = body.get("state")
        
        if not code:
            return JSONResponse(
                {"success": False, "error": "Authorization code required"},
                status_code=400
            )
        
        import requests
        import os
        
        # Exchange code for access token
        token_response = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": os.getenv("GITHUB_ID"),
                "client_secret": os.getenv("GITHUB_SECRET"),
                "code": code,
            }
        )
        
        token_data = token_response.json()
        
        if "error" in token_data:
            return JSONResponse(
                {"success": False, "error": f"GitHub OAuth error: {token_data.get('error_description', token_data['error'])}"},
                status_code=400
            )
        
        access_token = token_data.get("access_token")
        
        # Get user info
        user_response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        
        user_data = user_response.json()
        
        # Get user email if not public
        email = user_data.get("email")
        if not email:
            email_response = requests.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
            emails = email_response.json()
            primary_email = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
            email = primary_email.get("email") if primary_email else None
        
        if not email:
            return JSONResponse(
                {"success": False, "error": "Unable to get email from GitHub account"},
                status_code=400
            )
        
        # Create or update user
        user = await user_service.create_or_update_user_oauth(
            email=email,
            display_name=user_data.get("name") or user_data.get("login"),
            avatar_url=user_data.get("avatar_url"),
            github_id=str(user_data.get("id")),
            username=user_data.get("login")
        )
        
        # Generate JWT token
        token_data = {
            "sub": user.email,
            "email": user.email,
            "display_name": user.display_name,
            "provider": "github"
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
                "wallet_address": user.wallet_address,
                "user_id": user.id
            }
        })
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": "GitHub OAuth authentication failed"},
            status_code=500
        )


async def oauth_callback(request: Request):
    """Handle OAuth callbacks for Google/GitHub."""
    try:
        body = await request.json()
        provider = body.get("provider")  # "google" or "github"
        user_data = body.get("user")  # OAuth user data
        
        if not provider or not user_data:
            return JSONResponse(
                {"success": False, "error": "Invalid OAuth data"},
                status_code=400
            )
        
        email = user_data.get("email")
        name = user_data.get("name", email)
        avatar_url = user_data.get("picture") or user_data.get("avatar_url")
        provider_id = user_data.get("id") or user_data.get("sub")
        
        if not email:
            return JSONResponse(
                {"success": False, "error": "Email required from OAuth provider"},
                status_code=400
            )
        
        # Create or update user based on provider
        if provider == "google":
            user = await user_service.create_or_update_user_oauth(
                email=email,
                display_name=name,
                avatar_url=avatar_url,
                google_id=str(provider_id)
            )
        elif provider == "github":
            user = await user_service.create_or_update_user_oauth(
                email=email,
                display_name=name,
                avatar_url=avatar_url,
                github_id=str(provider_id),
                username=user_data.get("login") or user_data.get("username")
            )
        else:
            return JSONResponse(
                {"success": False, "error": "Unsupported OAuth provider"},
                status_code=400
            )
        
        # Generate JWT token
        token_data = {
            "sub": user.email,
            "email": user.email,
            "display_name": user.display_name,
            "provider": provider
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
                "wallet_address": user.wallet_address,
                "user_id": user.id
            }
        })
        
    except Exception as e:
        return JSONResponse(
            {"success": False, "error": "OAuth authentication failed"},
            status_code=500
        )


router = Router(routes=[
    Route("/", auth_status, methods=["GET"]),
    Route("/magic-link", send_magic_link, methods=["POST"]),
    Route("/verify", verify_magic_link, methods=["POST"]),
    Route("/oauth", oauth_callback, methods=["POST"]),
    Route("/oauth/github", github_oauth_callback, methods=["POST"]),
    Route("/session", create_session, methods=["POST"]),  # Restored for backward compatibility
    Route("/me", get_current_user, methods=["GET"])
])

"""
Authentication API Endpoints

1. GET /auth/ - Auth Status
  curl -X GET http://localhost:8000/auth/

2. POST /auth/magic-link - Send Magic Link
  curl -X POST http://localhost:8000/auth/magic-link \
    -H "Content-Type: application/json" \
    -d '{
      "email": "user@example.com",
      "display_name": "John Doe"
    }'

3. POST /auth/verify - Verify Magic Link Token
  curl -X POST http://localhost:8000/auth/verify \
    -H "Content-Type: application/json" \
    -d '{
      "token": "magic_link_token_here"
    }'

4. POST /auth/oauth - OAuth Authentication (Google/GitHub)
  curl -X POST http://localhost:8000/auth/oauth \
    -H "Content-Type: application/json" \
    -d '{
      "provider": "google",
      "user": {
        "id": "google_user_id",
        "email": "user@gmail.com",
        "name": "John Doe",
        "picture": "https://example.com/avatar.jpg"
      }
    }'

5. GET /auth/me - Get Current User (requires Bearer token)
  curl -X GET http://localhost:8000/auth/me \
    -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"

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