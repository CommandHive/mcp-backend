import os
import secrets
from datetime import datetime
from typing import Optional
from jose import JWTError, jwt


JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
NONCE_EXPIRATION_MINUTES = 5


class AuthService:
    @staticmethod
    def create_access_token(data: dict) -> str:
        """Create a JWT access token with expiration."""
        to_encode = data.copy()
        # JWT expiration in seconds from now
        import time
        expire = int(time.time()) + (JWT_EXPIRATION_HOURS * 3600)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError:
            return None

    @staticmethod
    def generate_nonce() -> str:
        """Generate a cryptographically secure random nonce."""
        return secrets.token_hex(16)

    @staticmethod
    def create_sign_message(nonce: str, wallet_address: str) -> str:
        """Create the message that users need to sign for authentication."""
        return f"Please sign this message to authenticate with CommandHive , nonce: {nonce} and wallet: {wallet_address}"
    

    @staticmethod
    def get_jwt_expiration_seconds() -> int:
        """Get JWT expiration time in seconds."""
        return JWT_EXPIRATION_HOURS * 3600



auth_service = AuthService()