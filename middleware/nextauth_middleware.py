from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from services.supabase_client import supabase_client
from services.auth_service import auth_service
from services.user_service import user_service
from datetime import datetime
import traceback


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate JWT access tokens."""
    
    # Endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        '/auth/',
        '/auth/validate',
        '/auth/sync',
        '/test/',
        '/verify/',
        '/'
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT access token if needed."""
        print(f"🔒 [JWTAuthMiddleware] Processing request: {request.method} {request.url.path}")
        
        # Skip auth for public endpoints
        if self.is_public_endpoint(request.url.path):
            print(f"🔒 [JWTAuthMiddleware] Public endpoint, skipping auth: {request.url.path}")
            return await call_next(request)
        
        # Extract and validate JWT access token
        try:
            auth_header = request.headers.get('Authorization')
            print(f"🔒 [JWTAuthMiddleware] Auth header: {auth_header}")
            
            if not auth_header or not auth_header.startswith('Bearer '):
                print("🔒 [JWTAuthMiddleware] Missing or invalid authorization header")
                return JSONResponse(
                    {'success': False, 'error': 'Missing or invalid authorization header'}, 
                    status_code=401
                )
            
            jwt_token = auth_header.split(' ')[1]
            print(f"🔒 [JWTAuthMiddleware] Extracted JWT token (first 20 chars): {jwt_token[:20]}...")
            
            # Validate JWT token
            user_data = await self.validate_jwt_token(jwt_token)
            if not user_data:
                print("🔒 [JWTAuthMiddleware] Invalid or expired JWT token")
                return JSONResponse(
                    {'success': False, 'error': 'Invalid or expired token'}, 
                    status_code=401
                )
            
            # Add user info to request state
            request.state.user = user_data
            print(f"✅ [JWTAuthMiddleware] JWT validated for user: {user_data.get('email')}")
            
            return await call_next(request)
            
        except Exception as e:
            print(f"❌ [JWTAuthMiddleware] Error validating JWT: {e}")
            print(f"❌ [JWTAuthMiddleware] Traceback: {traceback.format_exc()}")
            return JSONResponse(
                {'success': False, 'error': 'Authentication failed'}, 
                status_code=500
            )
    
    def is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (doesn't require authentication)."""
        # Exact match first
        if path in self.PUBLIC_ENDPOINTS:
            return True
        
        # Check prefix matches for nested routes
        for public_path in self.PUBLIC_ENDPOINTS:
            if path.startswith(public_path):
                return True
        
        return False
    
    async def validate_jwt_token(self, jwt_token: str) -> dict:
        """Validate JWT access token and get user data."""
        try:
            print(f"🔍 [JWTAuthMiddleware] Validating JWT token...")
            print(f"🔍 [JWTAuthMiddleware] JWT token (first 20 chars): {jwt_token[:20]}...")
            
            # Verify JWT token using auth_service
            payload = auth_service.verify_token(jwt_token)
            if not payload:
                print("❌ [JWTAuthMiddleware] JWT token verification failed")
                return None
            
            print(f"✅ [JWTAuthMiddleware] JWT token verified, payload: {payload}")
            
            # Extract email from payload
            email = payload.get('sub') or payload.get('email')
            if not email:
                print("❌ [JWTAuthMiddleware] No email found in JWT payload")
                return None
            
            # Get user data from database using email
            user = await user_service.get_user_by_email(email)
            if not user:
                print(f"❌ [JWTAuthMiddleware] User not found in database: {email}")
                return None
            
            # Convert user object to dict for request.state
            user_data = {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "username": user.username,
                "google_id": user.google_id,
                "github_id": user.github_id,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "wallet_address": user.wallet_address
            }
            
            print(f"✅ [JWTAuthMiddleware] User data retrieved: {user_data['email']}")
            return user_data
                
        except Exception as e:
            print(f"❌ [JWTAuthMiddleware] Error validating JWT token: {e}")
            print(f"❌ [JWTAuthMiddleware] Traceback: {traceback.format_exc()}")
            return None