#!/usr/bin/env python3
"""
Setup script for Radicale integration
Creates default users and initializes collections
"""

import os
import subprocess
import sys

def create_radicale_user(username, password):
    """Create a Radicale user using htpasswd"""
    try:
        # Create users directory if it doesn't exist
        os.makedirs("radicale_data", exist_ok=True)
        
        # Create user with htpasswd
        cmd = f"htpasswd -b radicale_data/users {username} {password}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Created user: {username}")
            return True
        else:
            print(f"✗ Failed to create user {username}: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error creating user {username}: {str(e)}")
        return False

def setup_radicale():
    """Setup Radicale with default configuration"""
    print("Setting up Radicale integration...")
    
    # Create necessary directories
    os.makedirs("radicale_data", exist_ok=True)
    os.makedirs("radicale_config", exist_ok=True)
    
    # Create default users
    users = [
        ("admin", "admin"),
        ("user1", "password1"),
        ("user2", "password2")
    ]
    
    for username, password in users:
        create_radicale_user(username, password)
    
    print("\n✓ Radicale setup complete!")
    print("\nDefault users created:")
    for username, password in users:
        print(f"  - {username}:{password}")
    
    print(f"\nRadicale will be available at: http://localhost:5232")
    print("FastAPI will be available at: http://localhost:8000")

if __name__ == "__main__":
    setup_radicale() 