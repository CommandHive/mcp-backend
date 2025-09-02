from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    id: Optional[str] = None  # NextAuth UUID
    wallet_address: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    display_name: str
    avatar_url: Optional[str] = None
    github_id: Optional[str] = None
    google_id: Optional[str] = None
    magic_link_token: Optional[str] = None  # For passwordless authentication
    magic_link_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True
    subscription_tier: str = "free"
    nonce: Optional[str] = None
    nonce_expires_at: Optional[datetime] = None
    password_hash: Optional[str] = None


class WalletAuthRequest(BaseModel):
    wallet_address: str


class WalletVerifyRequest(BaseModel):
    wallet_address: str
    signature: str
    nonce: str


class NextAuthUserRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    image: Optional[str] = None
    provider: str  # "email", "google", "github"
    provider_id: Optional[str] = None  # ID from the OAuth provider
    username: Optional[str] = None  # For GitHub


class EmailAuthRequest(BaseModel):
    email: EmailStr

class MagicLinkRequest(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None

class MagicLinkVerifyRequest(BaseModel):
    token: str