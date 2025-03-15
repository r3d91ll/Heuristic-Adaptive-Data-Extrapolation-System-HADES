#!/usr/bin/env python
"""
Test script for PostgreSQL-based authentication module.
This script demonstrates how to use the pg_auth module in a FastAPI application.
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env.test
try:
    from dotenv import load_dotenv
    env_file = project_root / ".env.test"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment variables from {env_file}")
    else:
        print(f"Warning: .env.test file not found at {env_file}")
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")

# Import the authentication module
from hades.auth.pg_auth import get_api_key, create_api_key

# Create a FastAPI application
app = FastAPI(title="HADES API Authentication Test")

@app.get("/")
async def root():
    """Public endpoint that doesn't require authentication."""
    return {"message": "Welcome to HADES API Authentication Test"}

@app.get("/secure")
async def secure_endpoint(key_info=Depends(get_api_key)):
    """Secure endpoint that requires API key authentication."""
    return {
        "message": "Authentication successful",
        "key_id": key_info["key_id"],
        "name": key_info["name"]
    }

@app.get("/admin")
async def admin_endpoint(key_info=Depends(get_api_key)):
    """Admin endpoint with additional authorization check."""
    # Example of role-based access control
    if key_info["name"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    
    return {
        "message": "Admin access granted",
        "key_id": key_info["key_id"]
    }

# Test client for the application
client = TestClient(app)

def test_public_endpoint():
    """Test the public endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to HADES API Authentication Test"}

def test_secure_endpoint_no_key():
    """Test the secure endpoint without an API key."""
    response = client.get("/secure")
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]

def test_secure_endpoint_with_key(api_key):
    """Test the secure endpoint with a valid API key."""
    response = client.get("/secure", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    assert "Authentication successful" in response.json()["message"]

def test_admin_endpoint(api_key, admin_key):
    """Test the admin endpoint with regular and admin keys."""
    # Regular user should be forbidden
    response = client.get("/admin", headers={"X-API-Key": api_key})
    assert response.status_code == 403
    
    # Admin should be allowed
    response = client.get("/admin", headers={"X-API-Key": admin_key})
    assert response.status_code == 200
    assert "Admin access granted" in response.json()["message"]

def create_test_keys():
    """Create test API keys for testing."""
    try:
        # Create a regular user key
        user_key = create_api_key("test_user")
        print(f"Created test user API key: {user_key['api_key']}")
        
        # Create an admin key
        admin_key = create_api_key("admin")
        print(f"Created admin API key: {admin_key['api_key']}")
        
        return user_key["api_key"], admin_key["api_key"]
    except Exception as e:
        print(f"Error creating test keys: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Testing PostgreSQL-based authentication module")
    
    # Check if authentication is enabled
    if os.environ.get("ENABLE_AUTH", "true").lower() != "true":
        print("Warning: Authentication is disabled. Set ENABLE_AUTH=true to enable.")
    
    # Create test keys
    user_key, admin_key = create_test_keys()
    
    # Run tests
    print("\nRunning tests:")
    print("1. Testing public endpoint...")
    test_public_endpoint()
    print("✓ Public endpoint test passed")
    
    print("2. Testing secure endpoint without API key...")
    test_secure_endpoint_no_key()
    print("✓ Secure endpoint (no key) test passed")
    
    print("3. Testing secure endpoint with valid API key...")
    test_secure_endpoint_with_key(user_key)
    print("✓ Secure endpoint (with key) test passed")
    
    print("4. Testing admin endpoint...")
    test_admin_endpoint(user_key, admin_key)
    print("✓ Admin endpoint test passed")
    
    print("\nAll tests passed successfully!")
    print("\nYou can now use these API keys for testing:")
    print(f"User API Key: {user_key}")
    print(f"Admin API Key: {admin_key}")
    print("\nExample usage with curl:")
    print(f"curl -H 'X-API-Key: {user_key}' http://localhost:8000/secure")
    print(f"curl -H 'X-API-Key: {admin_key}' http://localhost:8000/admin")
