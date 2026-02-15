#!/usr/bin/env python3
"""
Setup script to create the first admin user for the Electrician Work Log System
Run this script once to create an initial admin account
"""

import sqlite3
import bcrypt
import os
from getpass import getpass


def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_admin_user():
    """Create the first admin user"""
    db_path = os.path.join(os.path.dirname(__file__), 'database.db')

    if not os.path.exists(db_path):
        print(
            "❌ Database not found. Please run the Flask app first to create the database.")
        return False

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Check if any admin users already exist
        existing_admin = conn.execute(
            "SELECT id FROM users WHERE role = 'admin'"
        ).fetchone()

        if existing_admin:
            print(
                "⚠️  An admin user already exists. Use the user_manager.py tool to manage users.")
            conn.close()
            return False

        print("🔐 Creating first admin user for Electrician Work Log System")
        print("=" * 60)

        # Get user input
        username = input("Enter admin username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            conn.close()
            return False

        # Check if username already exists
        existing_user = conn.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()

        if existing_user:
            print(f"❌ Username '{username}' already exists")
            conn.close()
            return False

        full_name = input("Enter full name: ").strip()
        if not full_name:
            print("❌ Full name cannot be empty")
            conn.close()
            return False

        password = getpass("Enter password (min 4 characters): ")
        if len(password) < 4:
            print("❌ Password must be at least 4 characters long")
            conn.close()
            return False

        password_confirm = getpass("Confirm password: ")
        if password != password_confirm:
            print("❌ Passwords do not match")
            conn.close()
            return False

        # Hash password and create user
        password_hash = hash_password(password)

        conn.execute('''
            INSERT INTO users (username, password_hash, full_name, role, is_active)
            VALUES (?, ?, ?, 'admin', 1)
        ''', (username, password_hash, full_name))

        conn.commit()
        conn.close()

        print("=" * 60)
        print("✅ Admin user created successfully!")
        print(f"   Username: {username}")
        print(f"   Full Name: {full_name}")
        print(f"   Role: admin")
        print("=" * 60)
        print("🚀 You can now:")
        print("   1. Start the Flask server: python app.py")
        print("   2. Open login.html in your browser")
        print("   3. Use the user_manager.py tool to add more users")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False


if __name__ == "__main__":
    create_admin_user()
