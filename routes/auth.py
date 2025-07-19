from starlette.routing import Route, Router
from starlette.responses import JSONResponse
from starlette.requests import Request
from datetime import datetime
from models.user import WalletAuthRequest, WalletVerifyRequest
from services.auth_service import auth_service
from services.crypto_service import crypto_service
from services.user_service import user_service


async def request_nonce(request: Request):
    """Request a nonce for wallet authentication."""
    try:
        body = await request.json()
        wallet_request = WalletAuthRequest(**body)
        
        # Validate wallet address format
        if not crypto_service.is_valid_ethereum_address(wallet_request.wallet_address):
            return JSONResponse(
                {"success": False, "error": "Invalid wallet address format"},
                status_code=400
            )
        
        # Generate nonce
        nonce = auth_service.generate_nonce()
        
        # Create or update user with nonce
        user = await user_service.create_or_update_user_with_nonce(
            wallet_request.wallet_address, nonce
        )
        
        # Create message to sign
        message = auth_service.create_sign_message(nonce, wallet_request.wallet_address)
        
        return JSONResponse({
            "success": True,
            "nonce": nonce,
            "message": message
        })
        
    except Exception as e:
        print(f"Error in request_nonce: {e}")
        return JSONResponse(
            {"success": False, "error": "Failed to generate nonce"},
            status_code=500
        )


async def verify_wallet(request: Request):
    """Verify wallet signature and return JWT token."""
    try:
        body = await request.json()
        verify_request = WalletVerifyRequest(**body)
        
        # Validate wallet address format
        if not crypto_service.is_valid_ethereum_address(verify_request.wallet_address):
            return JSONResponse(
                {"success": False, "error": "Invalid wallet address format"},
                status_code=400
            )
        
        # Get user and validate nonce
        user = await user_service.get_user_by_wallet(verify_request.wallet_address)
        if not user or not user.nonce:
            return JSONResponse(
                {"success": False, "error": "Invalid or expired nonce"},
                status_code=400
            )
        
        # Check nonce match
        if user.nonce != verify_request.nonce:
            return JSONResponse(
                {"success": False, "error": "Invalid nonce"},
                status_code=400
            )
        
        
        # Verify signature
        message = auth_service.create_sign_message(verify_request.nonce, verify_request.wallet_address)
        if not crypto_service.verify_signature(message, verify_request.signature, verify_request.wallet_address):
            return JSONResponse(
                {"success": False, "error": "Invalid signature"},
                status_code=400
            )
        
        # Clear nonce after successful verification
        await user_service.clear_user_nonce(verify_request.wallet_address)
        
        # Generate JWT token
        token_data = {
            "sub": user.wallet_address,
            "wallet_address": user.wallet_address,
            "display_name": user.display_name
        }
        access_token = auth_service.create_access_token(token_data)
        
        return JSONResponse({
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.get_jwt_expiration_seconds(),
            "user": {
                "wallet_address": user.wallet_address,
                "display_name": user.display_name,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active
            }
        })
        
    except Exception as e:
        print(f"Error in verify_wallet: {e}")
        return JSONResponse(
            {"success": False, "error": "Verification failed"},
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
        
        # Get wallet address from token
        wallet_address = payload.get("sub")
        if not wallet_address:
            return JSONResponse(
                {"success": False, "error": "Invalid token payload"},
                status_code=401
            )
        
        # Get user from database
        user = await user_service.get_user_by_wallet(wallet_address)
        if not user:
            return JSONResponse(
                {"success": False, "error": "User not found"},
                status_code=404
            )
        
        return JSONResponse({
            "success": True,
            "user": {
                "wallet_address": user.wallet_address,
                "display_name": user.display_name,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "email": user.email,
                "username": user.username,
                "avatar_url": user.avatar_url
            }
        })
        
    except Exception as e:
        print(f"Error in get_current_user: {e}")
        return JSONResponse(
            {"success": False, "error": "Failed to get user"},
            status_code=500
        )


async def logout(request: Request):
    """Logout endpoint (client-side token removal)."""
    return JSONResponse({
        "success": True,
        "message": "Logged out successfully. Please remove the token from your client."
    })


async def auth_status(request: Request):
    """Auth API status and documentation."""
    return JSONResponse({
        "success": True,
        "message": "CommandHive Wallet Auth API",
        "version": "1.0.0",
        "flow": [
            "1. Connect wallet via Reown/WalletConnect on frontend",
            "2. POST /nonce with wallet_address to get nonce",
            "3. Sign the provided message with wallet",
            "4. POST /verify with wallet_address, signature, and nonce",
            "5. Receive JWT token for authenticated requests",
            "6. Use Bearer token in Authorization header"
        ],
        "endpoints": {
            "POST /nonce": "Request nonce for wallet authentication",
            "POST /verify": "Verify wallet signature and get JWT token",
            "GET /me": "Get current user info (requires Bearer token)",
            "POST /logout": "Logout (client-side token removal)",
            "GET /": "This status endpoint"
        }
    })


router = Router(routes=[
    Route("/", auth_status, methods=["GET"]),
    Route("/nonce", request_nonce, methods=["POST"]),
    Route("/verify", verify_wallet, methods=["POST"]),
    Route("/me", get_current_user, methods=["GET"]),
    Route("/logout", logout, methods=["POST"])
])

'''
Testing it out in LocalHost!

curl -X GET "http://0.0.0.0:8000/auth/" \
     -H "Accept: application/json"

curl -X POST "http://0.0.0.0:8000/auth/nonce" \
     -H "Content-Type: application/json" \
     -d '{"wallet_address":"0x293D3a1D4261570Bf30F0670cD41B5200Dc0A08f"}'

curl -X POST "http://0.0.0.0:8000/auth/verify" \
     -H "Content-Type: application/json" \
     -d '{
           "wallet_address":"0x293D3a1D4261570Bf30F0670cD41B5200Dc0A08f",
           "nonce":"b000d8633e0d063a2521330776c8ad20",
           "signature":""
         }'
{"success":true,"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIweDI5M2QzYTFkNDI2MTU3MGJmMzBmMDY3MGNkNDFiNTIwMGRjMGEwOGYiLCJ3YWxsZXRfYWRkcmVzcyI6IjB4MjkzZDNhMWQ0MjYxNTcwYmYzMGYwNjcwY2Q0MWI1MjAwZGMwYTA4ZiIsImRpc3BsYXlfbmFtZSI6IlVzZXJfMHgyOTNkM2EiLCJleHAiOjE3NTMwMTg3NDh9.Dh98KTpePE5lns4jKFjBNRrsYc0n6a5TZUGqFz4oMdk","token_type":"bearer","expires_in":86400,"user":{"wallet_address":"0x293d3a1d4261570bf30f0670cd41b5200dc0a08f","display_name":"User_0x293d3a","subscription_tier":"free","is_active":true}}%

curl -X GET "http://0.0.0.0:8000/auth/me" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIweDI5M2QzYTFkNDI2MTU3MGJmMzBmMDY3MGNkNDFiNTIwMGRjMGEwOGYiLCJ3YWxsZXRfYWRkcmVzcyI6IjB4MjkzZDNhMWQ0MjYxNTcwYmYzMGYwNjcwY2Q0MWI1MjAwZGMwYTA4ZiIsImRpc3BsYXlfbmFtZSI6IlVzZXJfMHgyOTNkM2EiLCJleHAiOjE3NTMwMTg3NDh9.Dh98KTpePE5lns4jKFjBNRrsYc0n6a5TZUGqFz4oMdk" \
     -H "Accept: application/json"

curl -X POST "http://0.0.0.0:8000/auth/logout" \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIweDI5M2QzYTFkNDI2MTU3MGJmMzBmMDY3MGNkNDFiNTIwMGRjMGEwOGYiLCJ3YWxsZXRfYWRkcmVzcyI6IjB4MjkzZDNhMWQ0MjYxNTcwYmYzMGYwNjcwY2Q0MWI1MjAwZGMwYTA4ZiIsImRpc3BsYXlfbmFtZSI6IlVzZXJfMHgyOTNkM2EiLCJleHAiOjE3NTMwMTg3NDh9.Dh98KTpePE5lns4jKFjBNRrsYc0n6a5TZUGqFz4oMdk" \
     -H "Accept: application/json"
{"success":true,"message":"Logged out successfully. Please remove the token from your client."}%

'''