#!/usr/bin/env python3
"""
Create a test account for Subjugate Online
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from subjugate_online.shared.database import DatabaseManager, Account
from subjugate_online.shared.utils import hash_password

def create_test_account():
    """Create a test account"""
    db_manager = DatabaseManager('postgresql://subjugate:subjugate123@localhost:5432/subjugate_online')

    # Create tables if they don't exist
    db_manager.create_all_tables()
    db_manager.initialize_world_data()

    session = db_manager.get_session()

    try:
        # Check if account exists
        existing = session.query(Account).filter_by(username='testuser').first()

        if existing:
            print("Test account 'testuser' already exists")
            return

        # Create account
        password_hash = hash_password('password123')
        account = Account(
            username='testuser',
            password_hash=password_hash,
            email='test@subjugate.online'
        )

        session.add(account)
        session.commit()

        print("Test account created successfully!")
        print("  Username: testuser")
        print("  Password: password123")
        print("  Email: test@subjugate.online")

    except Exception as e:
        print(f"Error creating account: {e}")
        session.rollback()
    finally:
        db_manager.close_session(session)


if __name__ == "__main__":
    create_test_account()
