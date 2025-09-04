from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from services.auth_service import auth_service
from services.user_service import user_service
import traceback


class JWTMiddleware(BaseHTTPMiddleware):
    """Middleware to validate JWT tokens for authentication."""
    
    # Endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        '/auth/',
        '/auth/magic-link',
        '/auth/verify',
        '/auth/oauth',
        '/auth/session',  # Keep for backward compatibility
        '/test/',
        '/verify/',
        '/chat/status'
    }
    
    # Protected endpoints that require authentication (takes precedence over public prefixes)
    PROTECTED_ENDPOINTS = {
        '/auth/me'
    }
    
    # Exact path matches that don't require authentication
    EXACT_PUBLIC_ENDPOINTS = {
        '/'
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT token if needed."""
        print(f"🔒 [JWTMiddleware] Processing request: {request.method} {request.url.path}")
        
        # TEMPORARY: Skip auth for testing - comment out for production
        print(f"🔒 [JWTMiddleware] TEMPORARY: Skipping auth for testing")
        # Add mock user for testing
        request.state.user = {
            "id": "968b5879-75c5-4750-a20f-b21dd20b07d9",
            "email": "vaibhav.dkm@gmail.com", 
            "display_name": "Vaibhav Maheshwari",
            "username": None,
            "avatar_url": "https://lh3.googleusercontent.com/a/ACg8ocJZYJdMLyxZrcGw49mbIQ5iH5d-74MwgS_EwlBXDpoZbvLHtZEV=s96-c",
            "subscription_tier": "free",
            "is_active": True,
            "wallet_address": None
        }
        return await call_next(request)
        
        # Skip auth for public endpoints
        if self.is_public_endpoint(request.url.path):
            print(f"🔒 [JWTMiddleware] Public endpoint, skipping auth: {request.url.path}")
            return await call_next(request)
        
        # Extract and validate JWT token
        try:
            auth_header = request.headers.get('Authorization')
            print(f"🔒 [JWTMiddleware] Auth header: {auth_header}")
            
            if not auth_header or not auth_header.startswith('Bearer '):
                print("🔒 [JWTMiddleware] Missing or invalid authorization header")
                return JSONResponse(
                    {'success': False, 'error': 'Missing or invalid authorization header'}, 
                    status_code=401
                )
            
            jwt_token = auth_header.split(' ')[1]
            print(f"🔒 [JWTMiddleware] Extracted JWT token (first 20 chars): {jwt_token[:20]}...")
            
            # Validate JWT token
            payload = auth_service.verify_token(jwt_token)
            if not payload:
                print("🔒 [JWTMiddleware] Invalid or expired JWT token")
                return JSONResponse(
                    {'success': False, 'error': 'Invalid or expired token'}, 
                    status_code=401
                )
            
            # Get user data from payload
            email = payload.get('email')
            if not email:
                print("🔒 [JWTMiddleware] No email in JWT payload")
                return JSONResponse(
                    {'success': False, 'error': 'Invalid token payload'}, 
                    status_code=401
                )
            
            # Optionally fetch full user data from database
            user = await user_service.get_user_by_email(email)
            if not user:
                print(f"🔒 [JWTMiddleware] User not found: {email}")
                return JSONResponse(
                    {'success': False, 'error': 'User not found'}, 
                    status_code=401
                )
            
            # Add user info to request state
            user_data = {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "username": user.username,
                "avatar_url": user.avatar_url,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "wallet_address": user.wallet_address
            }
            request.state.user = user_data
            print(f"✅ [JWTMiddleware] JWT validated for user: {user.email}")
            
            return await call_next(request)
            
        except Exception as e:
            print(f"❌ [JWTMiddleware] Error validating JWT: {e}")
            print(f"❌ [JWTMiddleware] Traceback: {traceback.format_exc()}")
            return JSONResponse(
                {'success': False, 'error': 'Authentication failed'}, 
                status_code=500
            )
    
    def is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (doesn't require authentication)."""
        # Check if path is explicitly protected first
        if path in self.PROTECTED_ENDPOINTS:
            return False
            
        # Check exact matches
        if path in self.EXACT_PUBLIC_ENDPOINTS:
            return True
            
        # Check prefix matches for nested routes
        for public_path in self.PUBLIC_ENDPOINTS:
            if path.startswith(public_path):
                return True
        
        return False