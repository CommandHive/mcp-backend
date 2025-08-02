from datetime import datetime
from typing import Optional
from models.user import User
from services.supabase_client import supabase_client
from services.crypto_service import crypto_service


class UserService:
    @staticmethod
    async def get_user_by_wallet(wallet_address: str) -> Optional[User]:
        """Get user by wallet address (primary key)."""
        try:
            normalized_address = crypto_service.normalize_wallet_address(wallet_address)
            query = "SELECT * FROM users WHERE wallet_address = %s"
            result = supabase_client.execute_query(query, (normalized_address,))
            
            if result:
                user_data = dict(result[0])
                return User(**user_data)
            return None
            
        except Exception as e:
            print(f"Error fetching user by wallet: {e}")
            return None

    @staticmethod
    async def create_user(wallet_address: str, nonce: str = None) -> User:
        """Create a new user with wallet address as primary key."""
        try:
            normalized_address = crypto_service.normalize_wallet_address(wallet_address)
            display_name = f"User_{normalized_address[:8]}"
            current_time = datetime.utcnow()
            
            query = """
                INSERT INTO users (wallet_address, display_name, nonce, 
                                 created_at, updated_at, is_active, subscription_tier)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            supabase_client.execute_query(query, (
                normalized_address, display_name, nonce,
                current_time, current_time, True, "free"
            ))
            
            return User(
                wallet_address=normalized_address,
                display_name=display_name,
                nonce=nonce,
                created_at=current_time,
                updated_at=current_time,
                is_active=True,
                subscription_tier="free"
            )
            
        except Exception as e:
            print(f"Error creating user: {e}")
            raise

    @staticmethod
    async def update_user_nonce(wallet_address: str, nonce: str) -> bool:
        """Update user's nonce."""
        try:
            normalized_address = crypto_service.normalize_wallet_address(wallet_address)
            current_time = datetime.utcnow()
            
            query = """
                UPDATE users 
                SET nonce = %s, updated_at = %s 
                WHERE wallet_address = %s
            """
            result = supabase_client.execute_query(query, (
                nonce, current_time, normalized_address
            ))
            
            return result > 0
            
        except Exception as e:
            print(f"Error updating user nonce: {e}")
            return False

    @staticmethod
    async def clear_user_nonce(wallet_address: str) -> bool:
        """Clear user's nonce after successful authentication."""
        try:
            normalized_address = crypto_service.normalize_wallet_address(wallet_address)
            current_time = datetime.utcnow()
            
            query = """
                UPDATE users 
                SET nonce = NULL, updated_at = %s 
                WHERE wallet_address = %s
            """
            result = supabase_client.execute_query(query, (current_time, normalized_address))
            
            return result > 0
            
        except Exception as e:
            print(f"Error clearing user nonce: {e}")
            return False

    @staticmethod
    async def create_or_update_user_with_nonce(wallet_address: str, nonce: str) -> User:
        """Create user if doesn't exist, or update existing user with new nonce."""
        user = await UserService.get_user_by_wallet(wallet_address)
        
        if user:
            # Update existing user with new nonce
            await UserService.update_user_nonce(wallet_address, nonce)
            user.nonce = nonce
            return user
        else:
            # Create new user
            return await UserService.create_user(wallet_address, nonce)

    @staticmethod
    async def update_user_profile(wallet_address: str, **kwargs) -> bool:
        """Update user profile fields."""
        try:
            # Filter out None values and build dynamic query
            updates = {k: v for k, v in kwargs.items() if v is not None}
            if not updates:
                return True
            
            updates['updated_at'] = datetime.utcnow()
            normalized_address = crypto_service.normalize_wallet_address(wallet_address)
            
            set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
            query = f"UPDATE users SET {set_clause} WHERE wallet_address = %s"
            
            values = list(updates.values()) + [normalized_address]
            result = supabase_client.execute_query(query, values)
            
            return result > 0
            
        except Exception as e:
            print(f"Error updating user profile: {e}")
            return False

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email address."""
        try:
            query = "SELECT * FROM users WHERE email = %s"
            result = supabase_client.execute_query(query, (email,))
            
            if result:
                user_data = dict(result[0])
                return User(**user_data)
            return None
            
        except Exception as e:
            print(f"Error fetching user by email: {e}")
            return None

    @staticmethod
    async def create_or_update_user_by_email(email: str, display_name: str = None) -> User:
        """Create or update user by email address."""
        try:
            # Check if user exists
            user = await UserService.get_user_by_email(email)
            current_time = datetime.utcnow()
            
            if user:
                # Update existing user
                if display_name and display_name != user.display_name:
                    query = "UPDATE users SET display_name = %s, updated_at = %s WHERE email = %s"
                    supabase_client.execute_query(query, (display_name, current_time, email))
                    user.display_name = display_name
                    user.updated_at = current_time
                return user
            else:
                # Create new user
                if not display_name:
                    display_name = email.split('@')[0]
                
                query = """
                    INSERT INTO users (email, display_name, created_at, updated_at, 
                                     is_active, subscription_tier)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                supabase_client.execute_query(query, (
                    email, display_name, current_time, current_time, True, "free"
                ))
                
                return User(
                    email=email,
                    display_name=display_name,
                    created_at=current_time,
                    updated_at=current_time,
                    is_active=True,
                    subscription_tier="free"
                )
                
        except Exception as e:
            print(f"Error creating/updating user by email: {e}")
            raise

    @staticmethod
    async def create_or_update_user_oauth(email: str, display_name: str = None, 
                                        avatar_url: str = None, google_id: str = None,
                                        github_id: str = None, username: str = None) -> User:
        """Create or update user for OAuth providers (Google, GitHub)."""
        try:
            # Check if user exists
            user = await UserService.get_user_by_email(email)
            current_time = datetime.utcnow()
            
            if user:
                # Update existing user with OAuth data
                updates = {}
                if display_name and display_name != user.display_name:
                    updates['display_name'] = display_name
                if avatar_url and avatar_url != user.avatar_url:
                    updates['avatar_url'] = avatar_url
                if google_id and google_id != user.google_id:
                    updates['google_id'] = google_id
                if github_id and github_id != user.github_id:
                    updates['github_id'] = github_id
                if username and username != user.username:
                    updates['username'] = username
                
                if updates:
                    updates['updated_at'] = current_time
                    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                    query = f"UPDATE users SET {set_clause} WHERE email = %s"
                    values = list(updates.values()) + [email]
                    supabase_client.execute_query(query, values)
                    
                    # Update user object
                    for key, value in updates.items():
                        setattr(user, key, value)
                
                return user
            else:
                # Create new user with OAuth data
                if not display_name:
                    display_name = email.split('@')[0]
                
                query = """
                    INSERT INTO users (email, display_name, avatar_url, google_id, 
                                     github_id, username, created_at, updated_at, 
                                     is_active, subscription_tier)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                supabase_client.execute_query(query, (
                    email, display_name, avatar_url, google_id, github_id, 
                    username, current_time, current_time, True, "free"
                ))
                
                return User(
                    email=email,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    google_id=google_id,
                    github_id=github_id,
                    username=username,
                    created_at=current_time,
                    updated_at=current_time,
                    is_active=True,
                    subscription_tier="free"
                )
                
        except Exception as e:
            print(f"Error creating/updating user with OAuth: {e}")
            raise


user_service = UserService()