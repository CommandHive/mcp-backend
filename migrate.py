#!/usr/bin/env python3
"""
Database migration script for CommandHive backend.
Run this to create/update database tables.
"""

import os
import sys
from pathlib import Path
from services.supabase_client import supabase_client


def run_migration(migration_file: str):
    """Run a single migration file."""
    migration_path = Path(__file__).parent / "migrations" / migration_file
    
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    try:
        print(f"🔄 Running migration: {migration_file}")
        
        # Read the SQL file
        with open(migration_path, 'r') as f:
            sql_content = f.read()
        
        # Execute the migration
        supabase_client.execute_query(sql_content)
        
        print(f"✅ Migration completed: {migration_file}")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {migration_file}")
        print(f"Error: {e}")
        return False


def run_all_migrations():
    """Run all migration files in order."""
    migrations_dir = Path(__file__).parent / "migrations"
    
    if not migrations_dir.exists():
        print("❌ Migrations directory not found")
        return False
    
    # Get all .sql files and sort them
    migration_files = sorted([f.name for f in migrations_dir.glob("*.sql")])
    
    if not migration_files:
        print("⚠️  No migration files found")
        return True
    
    print(f"🚀 Found {len(migration_files)} migration(s)")
    
    # Run each migration
    success_count = 0
    for migration_file in migration_files:
        if run_migration(migration_file):
            success_count += 1
        else:
            print(f"❌ Stopping due to failed migration: {migration_file}")
            break
    
    print(f"\n📊 Migration Summary:")
    print(f"   ✅ Successful: {success_count}/{len(migration_files)}")
    
    if success_count == len(migration_files):
        print("🎉 All migrations completed successfully!")
        return True
    else:
        print("💥 Some migrations failed!")
        return False


def main():
    """Main migration runner."""
    print("🔧 CommandHive Database Migration Tool")
    print("=" * 40)
    
    # Check DATABASE_URL
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL environment variable not set")
        print("Please set DATABASE_URL and try again")
        sys.exit(1)
    
    # Run migrations
    success = run_all_migrations()
    
    if success:
        print("\n🎯 Database is ready!")
        sys.exit(0)
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()