#!/usr/bin/env python3

from models.init import drop_all_tables, create_tables

if __name__ == "__main__":
    print("Dropping all existing tables...")
    if drop_all_tables():
        print("Creating new tables with updated schema...")
        if create_tables():
            print("Database schema updated successfully!")
        else:
            print("Failed to create new tables!")
    else:
        print("Failed to drop existing tables!")