import os
import secrets
from datetime import datetime
from typing import Optional
from jose import JWTError, jwt
from prompts.constants import WALLET_SIGN_MESSAGE_TEMPLATE


JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
NONCE_EXPIRATION_MINUTES = 5


class AuthService:
    @staticmethod
    def create_access_token(data: dict) -> str:
        """Create a JWT access token with expiration."""
        print(f"🔐 [AuthService.create_access_token] Creating JWT token...")
        print(f"🔐 [AuthService.create_access_token] Input data: {data}")
        print(f"🔐 [AuthService.create_access_token] JWT_SECRET set: {bool(JWT_SECRET)}")
        print(f"🔐 [AuthService.create_access_token] JWT_ALGORITHM: {JWT_ALGORITHM}")
        print(f"🔐 [AuthService.create_access_token] JWT_EXPIRATION_HOURS: {JWT_EXPIRATION_HOURS}")
        
        to_encode = data.copy()
        # JWT expiration in seconds from now
        import time
        expire = int(time.time()) + (JWT_EXPIRATION_HOURS * 3600)
        to_encode.update({"exp": expire})
        
        print(f"🔐 [AuthService.create_access_token] Final payload to encode: {to_encode}")
        print(f"🔐 [AuthService.create_access_token] Expiration timestamp: {expire}")
        
        try:
            encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
            print(f"✅ [AuthService.create_access_token] JWT created successfully (first 20 chars): {encoded_jwt[:20]}...")
            return encoded_jwt
        except Exception as e:
            print(f"❌ [AuthService.create_access_token] Error creating JWT: {e}")
            raise

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode a JWT token."""
        print(f"🔐 [AuthService.verify_token] Verifying JWT token...")
        print(f"🔐 [AuthService.verify_token] Token (first 20 chars): {token[:20]}...")
        print(f"🔐 [AuthService.verify_token] JWT_SECRET set: {bool(JWT_SECRET)}")
        print(f"🔐 [AuthService.verify_token] JWT_ALGORITHM: {JWT_ALGORITHM}")
        
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            print(f"✅ [AuthService.verify_token] Token verified successfully")
            print(f"✅ [AuthService.verify_token] Payload: {payload}")
            return payload
        except JWTError as e:
            print(f"❌ [AuthService.verify_token] JWT verification failed: {e}")
            print(f"❌ [AuthService.verify_token] JWT error type: {type(e)}")
            return None

    @staticmethod
    def generate_nonce() -> str:
        """Generate a cryptographically secure random nonce."""
        return secrets.token_hex(16)

    @staticmethod
    def create_sign_message(nonce: str, wallet_address: str) -> str:
        """Create the message that users need to sign for authentication."""
        return WALLET_SIGN_MESSAGE_TEMPLATE.format(nonce=nonce, wallet_address=wallet_address)
    

    @staticmethod
    def get_jwt_expiration_seconds() -> int:
        """Get JWT expiration time in seconds."""
        return JWT_EXPIRATION_HOURS * 3600



auth_service = AuthService()