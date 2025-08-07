from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from services.supabase_client import supabase_client
from datetime import datetime
import traceback


class NextAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate NextAuth session tokens."""
    
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
        """Process request and validate NextAuth session if needed."""
        print(f"🔒 [NextAuthMiddleware] Processing request: {request.method} {request.url.path}")
        
        # Skip auth for public endpoints
        if self.is_public_endpoint(request.url.path):
            print(f"🔒 [NextAuthMiddleware] Public endpoint, skipping auth: {request.url.path}")
            return await call_next(request)
        
        # Extract and validate NextAuth session token
        try:
            auth_header = request.headers.get('Authorization')
            print(f"🔒 [NextAuthMiddleware] Auth header: {auth_header}")
            
            if not auth_header or not auth_header.startswith('Bearer '):
                print("🔒 [NextAuthMiddleware] Missing or invalid authorization header")
                return JSONResponse(
                    {'success': False, 'error': 'Missing or invalid authorization header'}, 
                    status_code=401
                )
            
            session_token = auth_header.split(' ')[1]
            print(f"🔒 [NextAuthMiddleware] Extracted session token (first 20 chars): {session_token[:20]}...")
            
            # Validate NextAuth session in database
            user_data = await self.validate_nextauth_session(session_token)
            if not user_data:
                print("🔒 [NextAuthMiddleware] Invalid or expired session")
                return JSONResponse(
                    {'success': False, 'error': 'Invalid or expired session'}, 
                    status_code=401
                )
            
            # Add user info to request state
            request.state.user = user_data
            print(f"✅ [NextAuthMiddleware] Session validated for user: {user_data.get('email')}")
            
            return await call_next(request)
            
        except Exception as e:
            print(f"❌ [NextAuthMiddleware] Error validating session: {e}")
            print(f"❌ [NextAuthMiddleware] Traceback: {traceback.format_exc()}")
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
    
    async def validate_nextauth_session(self, auth_token: str) -> dict:
        """Validate NextAuth session token or user ID against database."""
        try:
            print(f"🔍 [NextAuthMiddleware] Validating auth token in database...")
            print(f"🔍 [NextAuthMiddleware] Auth token (first 20 chars): {auth_token[:20]}...")
            
            # Check if this is a NextAuth user ID (starts with nextauth_user_)
            if auth_token.startswith('nextauth_user_'):
                user_id = auth_token.replace('nextauth_user_', '')
                print(f"🔍 [NextAuthMiddleware] Detected NextAuth user ID: {user_id}")
                
                # Query user directly by ID
                query = """
                    SELECT 
                        u.id,
                        u.email,
                        u.display_name,
                        u.avatar_url,
                        u.username,
                        u.google_id,
                        u.github_id,
                        u.subscription_tier,
                        u.is_active,
                        u.wallet_address
                    FROM users u 
                    WHERE u.id = %s
                """
                
                result = supabase_client.execute_query(query, (user_id,))
                print(f"🔍 [NextAuthMiddleware] User ID validation query result: {result}")
                
                if result:
                    user_data = dict(result[0])
                    print(f"✅ [NextAuthMiddleware] Valid user found for ID: {user_data['email']}")
                    return user_data
            elif auth_token.startswith('nextauth_'):
                # Handle base64 encoded NextAuth token
                try:
                    import base64
                    import json
                    
                    print(f"🔍 [NextAuthMiddleware] Detected NextAuth base64 token")
                    token_payload = auth_token.replace('nextauth_', '')
                    
                    # Decode the base64 token
                    decoded_data = base64.b64decode(token_payload).decode('utf-8')
                    auth_data = json.loads(decoded_data)
                    
                    print(f"🔍 [NextAuthMiddleware] Decoded auth data: {auth_data}")
                    
                    user_id = auth_data.get('user_id')
                    if user_id:
                        # Query user directly by ID
                        query = """
                            SELECT 
                                u.id,
                                u.email,
                                u.display_name,
                                u.avatar_url,
                                u.username,
                                u.google_id,
                                u.github_id,
                                u.subscription_tier,
                                u.is_active,
                                u.wallet_address
                            FROM users u 
                            WHERE u.id = %s
                        """
                        
                        result = supabase_client.execute_query(query, (user_id,))
                        print(f"🔍 [NextAuthMiddleware] Base64 token validation query result: {result}")
                        
                        if result:
                            user_data = dict(result[0])
                            print(f"✅ [NextAuthMiddleware] Valid user found for base64 token: {user_data['email']}")
                            return user_data
                except Exception as e:
                    print(f"❌ [NextAuthMiddleware] Error decoding base64 token: {e}")
            else:
                # Original session token validation
                print(f"🔍 [NextAuthMiddleware] Validating as session token...")
                
                # Query NextAuth sessions table with user data
                query = """
                    SELECT 
                        u.id,
                        u.email,
                        u.display_name,
                        u.avatar_url,
                        u.username,
                        u.google_id,
                        u.github_id,
                        u.subscription_tier,
                        u.is_active,
                        u.wallet_address,
                        s.expires,
                        s.session_token
                    FROM users u 
                    JOIN sessions s ON u.id = s.user_id 
                    WHERE s.session_token = %s AND s.expires > %s
                """
                
                current_time = datetime.utcnow()
                result = supabase_client.execute_query(query, (auth_token, current_time))
                print(f"🔍 [NextAuthMiddleware] Session validation query result: {result}")
                
                if result:
                    user_data = dict(result[0])
                    print(f"✅ [NextAuthMiddleware] Valid session found for user: {user_data['email']}")
                    return user_data
            
            print("❌ [NextAuthMiddleware] No valid session or user found")
            return None
                
        except Exception as e:
            print(f"❌ [NextAuthMiddleware] Error validating session: {e}")
            print(f"❌ [NextAuthMiddleware] Traceback: {traceback.format_exc()}")
            return None