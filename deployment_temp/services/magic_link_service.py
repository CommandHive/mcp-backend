import secrets
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from services.user_service import user_service
from services.email_service import email_service
from services.auth_service import auth_service


class MagicLinkService:
    """Service for handling passwordless authentication with magic links."""
    
    MAGIC_LINK_EXPIRY_MINUTES = 15  # Magic links expire in 15 minutes
    
    @staticmethod
    def generate_magic_token() -> str:
        """Generate a secure random token for magic links."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    async def send_magic_link(email: str, display_name: Optional[str] = None) -> dict:
        """
        Generate and send a magic link to the user's email.
        Creates user if they don't exist.
        """
        try:
            print(f"🔗 [MagicLinkService] Sending magic link to {email}")
            
            # Generate magic token
            magic_token = MagicLinkService.generate_magic_token()
            expiry_time = datetime.now(timezone.utc) + timedelta(minutes=MagicLinkService.MAGIC_LINK_EXPIRY_MINUTES)
            
            print(f"🔗 [MagicLinkService] Generated token: {magic_token[:10]}...")
            print(f"🔗 [MagicLinkService] Token expires at: {expiry_time}")
            
            # Check if user exists
            user = await user_service.get_user_by_email(email)
            is_new_user = user is None
            
            if is_new_user:
                print(f"🔗 [MagicLinkService] Creating new user for {email}")
                # Create new user
                user = await user_service.create_or_update_user_by_email(
                    email=email,
                    display_name=display_name or email.split('@')[0]
                )
            else:
                print(f"🔗 [MagicLinkService] User exists: {user.display_name}")
            
            # Store magic link token in user record
            await user_service.store_magic_link_token(email, magic_token, expiry_time)
            
            # Send magic link email
            email_sent = email_service.send_magic_link(
                email=email,
                token=magic_token,
                display_name=user.display_name
            )
            
            if not email_sent:
                print(f"❌ [MagicLinkService] Failed to send email to {email}")
                return {
                    "success": False,
                    "error": "Failed to send magic link email"
                }
            
            # Send welcome email for new users (non-blocking)
            if is_new_user:
                try:
                    email_service.send_welcome_email(email, user.display_name)
                except Exception as e:
                    print(f"⚠️ [MagicLinkService] Welcome email failed (non-critical): {e}")
            
            print(f"✅ [MagicLinkService] Magic link sent successfully to {email}")
            return {
                "success": True,
                "message": "Magic link sent to your email"
            }
            
        except Exception as e:
            print(f"❌ [MagicLinkService] Error sending magic link: {e}")
            import traceback
            print(f"❌ [MagicLinkService] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": "Failed to send magic link"
            }
    
    @staticmethod
    async def verify_magic_token(token: str) -> dict:
        """
        Verify magic link token and return JWT if valid.
        Token is invalidated after use.
        """
        try:
            print(f"🔐 [MagicLinkService] Verifying token: {token[:10]}...")
            
            # Find user with this magic token
            user = await user_service.get_user_by_magic_token(token)
            
            if not user:
                print(f"❌ [MagicLinkService] Invalid token: {token[:10]}...")
                return {
                    "success": False,
                    "error": "Invalid or expired magic link"
                }
            
            # Check if token is expired
            if user.magic_link_expires_at and datetime.now(timezone.utc) > user.magic_link_expires_at:
                print(f"❌ [MagicLinkService] Token expired for user: {user.email}")
                # Clear expired token
                await user_service.clear_magic_link_token(user.email)
                return {
                    "success": False,
                    "error": "Magic link has expired"
                }
            
            print(f"✅ [MagicLinkService] Token verified for user: {user.email}")
            
            # Clear the magic link token (single use)
            await user_service.clear_magic_link_token(user.email)
            
            # Generate JWT token
            token_data = {
                "sub": user.email,
                "email": user.email,
                "display_name": user.display_name,
                "provider": "magic_link"
            }
            
            access_token = auth_service.create_access_token(token_data)
            
            return {
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
            }
            
        except Exception as e:
            print(f"❌ [MagicLinkService] Error verifying token: {e}")
            import traceback
            print(f"❌ [MagicLinkService] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": "Failed to verify magic link"
            }


magic_link_service = MagicLinkService()