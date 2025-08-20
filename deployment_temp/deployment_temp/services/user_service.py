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
        print(f"🔍 [UserService.get_user_by_email] Looking up user by email: {email}")
        
        try:
            query = "SELECT * FROM users WHERE email = %s"
            print(f"🔍 [UserService.get_user_by_email] Query: {query}")
            print(f"🔍 [UserService.get_user_by_email] Parameters: ({email},)")
            
            result = supabase_client.execute_query(query, (email,))
            print(f"🔍 [UserService.get_user_by_email] Query result: {result}")
            
            if result:
                user_data = dict(result[0])
                print(f"✅ [UserService.get_user_by_email] User found: {user_data}")
                user = User(**user_data)
                print(f"✅ [UserService.get_user_by_email] User object created: {user}")
                return user
            else:
                print(f"❌ [UserService.get_user_by_email] No user found with email: {email}")
                return None
            
        except Exception as e:
            print(f"❌ [UserService.get_user_by_email] Error fetching user by email: {e}")
            print(f"❌ [UserService.get_user_by_email] Error type: {type(e)}")
            import traceback
            print(f"❌ [UserService.get_user_by_email] Traceback: {traceback.format_exc()}")
            return None

    @staticmethod
    async def get_user_with_password(email: str) -> Optional[dict]:
        """Get user with password hash for authentication."""
        try:
            query = "SELECT * FROM users WHERE email = %s"
            result = supabase_client.execute_query(query, (email,))
            
            if result:
                return dict(result[0])
            return None
            
        except Exception as e:
            print(f"Error fetching user with password: {e}")
            return None

    @staticmethod
    async def store_magic_link_token(email: str, token: str, expires_at: datetime) -> bool:
        """Store magic link token for user."""
        try:
            query = """
                UPDATE users 
                SET magic_link_token = %s, magic_link_expires_at = %s, updated_at = %s 
                WHERE email = %s
            """
            current_time = datetime.utcnow()
            result = supabase_client.execute_query(query, (token, expires_at, current_time, email))
            return result > 0
        except Exception as e:
            print(f"Error storing magic link token: {e}")
            return False

    @staticmethod
    async def get_user_by_magic_token(token: str) -> Optional[User]:
        """Get user by magic link token."""
        try:
            query = "SELECT * FROM users WHERE magic_link_token = %s"
            result = supabase_client.execute_query(query, (token,))
            
            if result:
                user_data = dict(result[0])
                return User(**user_data)
            return None
        except Exception as e:
            print(f"Error fetching user by magic token: {e}")
            return None

    @staticmethod
    async def clear_magic_link_token(email: str) -> bool:
        """Clear magic link token after use."""
        try:
            query = """
                UPDATE users 
                SET magic_link_token = NULL, magic_link_expires_at = NULL, updated_at = %s 
                WHERE email = %s
            """
            current_time = datetime.utcnow()
            result = supabase_client.execute_query(query, (current_time, email))
            return result > 0
        except Exception as e:
            print(f"Error clearing magic link token: {e}")
            return False

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
                    RETURNING id
                """
                result = supabase_client.execute_query(query, (
                    email, display_name, current_time, current_time, True, "free"
                ))
                
                user_id = result[0]['id'] if result else None
                
                return User(
                    id=user_id,
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
                    RETURNING id
                """
                result = supabase_client.execute_query(query, (
                    email, display_name, avatar_url, google_id, github_id, 
                    username, current_time, current_time, True, "free"
                ))
                
                user_id = result[0]['id'] if result else None
                
                return User(
                    id=user_id,
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

    @staticmethod
    async def sync_nextauth_user(nextauth_user_id: str, email: str, **kwargs) -> User:
        """Sync user data from NextAuth database."""
        print(f"🔄 [UserService.sync_nextauth_user] Syncing NextAuth user...")
        print(f"🔄 [UserService.sync_nextauth_user] NextAuth User ID: {nextauth_user_id}")
        print(f"🔄 [UserService.sync_nextauth_user] Email: {email}")
        print(f"🔄 [UserService.sync_nextauth_user] Additional data: {kwargs}")
        
        try:
            # Check if user exists by NextAuth ID (primary) or email (fallback)
            query = """
                SELECT * FROM users 
                WHERE id = %s OR email = %s
                ORDER BY 
                    CASE WHEN id = %s THEN 1 ELSE 2 END
                LIMIT 1
            """
            result = supabase_client.execute_query(query, (nextauth_user_id, email, nextauth_user_id))
            print(f"🔄 [UserService.sync_nextauth_user] Query result: {result}")
            
            current_time = datetime.utcnow()
            
            if result:
                # Update existing user
                print("🔄 [UserService.sync_nextauth_user] Updating existing user...")
                user_data = dict(result[0])
                existing_user_id = user_data['id']
                
                # Prepare updates (only update non-None values)
                updates = {}
                if kwargs.get('display_name') and kwargs['display_name'] != user_data.get('display_name'):
                    updates['display_name'] = kwargs['display_name']
                if kwargs.get('avatar_url') and kwargs['avatar_url'] != user_data.get('avatar_url'):
                    updates['avatar_url'] = kwargs['avatar_url']
                if kwargs.get('google_id') and kwargs['google_id'] != user_data.get('google_id'):
                    updates['google_id'] = kwargs['google_id']
                if kwargs.get('github_id') and kwargs['github_id'] != user_data.get('github_id'):
                    updates['github_id'] = kwargs['github_id']
                if kwargs.get('username') and kwargs['username'] != user_data.get('username'):
                    updates['username'] = kwargs['username']
                
                # Ensure user has correct NextAuth ID if it's different
                if existing_user_id != nextauth_user_id:
                    updates['id'] = nextauth_user_id
                
                if updates:
                    updates['updated_at'] = current_time
                    set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                    update_query = f"UPDATE users SET {set_clause} WHERE id = %s"
                    values = list(updates.values()) + [existing_user_id]
                    
                    print(f"🔄 [UserService.sync_nextauth_user] Update query: {update_query}")
                    print(f"🔄 [UserService.sync_nextauth_user] Update values: {values}")
                    
                    supabase_client.execute_query(update_query, values)
                    
                    # Update user_data with new values
                    for key, value in updates.items():
                        user_data[key] = value
                
                print(f"✅ [UserService.sync_nextauth_user] User updated successfully")
                return User(**user_data)
                
            else:
                # This case should be rare with database strategy
                # NextAuth should create the user first, but handle it just in case
                print("⚠️ [UserService.sync_nextauth_user] User not found, creating new user...")
                
                display_name = kwargs.get('display_name') or email.split('@')[0]
                
                insert_query = """
                    INSERT INTO users (id, email, display_name, avatar_url, google_id, 
                                     github_id, username, created_at, updated_at, 
                                     is_active, subscription_tier)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                supabase_client.execute_query(insert_query, (
                    nextauth_user_id, email, display_name, kwargs.get('avatar_url'),
                    kwargs.get('google_id'), kwargs.get('github_id'), kwargs.get('username'),
                    current_time, current_time, True, "free"
                ))
                
                print(f"✅ [UserService.sync_nextauth_user] New user created successfully")
                
                return User(
                    id=nextauth_user_id,
                    email=email,
                    display_name=display_name,
                    avatar_url=kwargs.get('avatar_url'),
                    google_id=kwargs.get('google_id'),
                    github_id=kwargs.get('github_id'),
                    username=kwargs.get('username'),
                    created_at=current_time,
                    updated_at=current_time,
                    is_active=True,
                    subscription_tier="free"
                )
                
        except Exception as e:
            print(f"❌ [UserService.sync_nextauth_user] Error syncing NextAuth user: {e}")
            import traceback
            print(f"❌ [UserService.sync_nextauth_user] Traceback: {traceback.format_exc()}")
            raise

    @staticmethod
    async def get_user_by_nextauth_id(nextauth_user_id: str) -> Optional[User]:
        """Get user by NextAuth user ID."""
        print(f"🔍 [UserService.get_user_by_nextauth_id] Looking up user by NextAuth ID: {nextauth_user_id}")
        
        try:
            query = "SELECT * FROM users WHERE id = %s"
            result = supabase_client.execute_query(query, (nextauth_user_id,))
            print(f"🔍 [UserService.get_user_by_nextauth_id] Query result: {result}")
            
            if result:
                user_data = dict(result[0])
                print(f"✅ [UserService.get_user_by_nextauth_id] User found: {user_data['email']}")
                return User(**user_data)
            else:
                print(f"❌ [UserService.get_user_by_nextauth_id] No user found with NextAuth ID: {nextauth_user_id}")
                return None
                
        except Exception as e:
            print(f"❌ [UserService.get_user_by_nextauth_id] Error: {e}")
            import traceback
            print(f"❌ [UserService.get_user_by_nextauth_id] Traceback: {traceback.format_exc()}")
            return None


user_service = UserService()