"""
PostgreSQL test environment configuration.

This file contains the configuration for connecting to a PostgreSQL database for testing.
You can override these values by setting environment variables:
- HADES_TEST_DB_NAME
- HADES_TEST_DB_USER
- HADES_TEST_DB_PASSWORD
- HADES_TEST_DB_HOST
- HADES_TEST_DB_PORT
"""
import os
import sys
from pathlib import Path

# Load environment variables from .env.test file
try:
    from dotenv import load_dotenv
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env.test"
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded PostgreSQL credentials from {env_file}")
    else:
        print(f"Warning: .env.test file not found at {env_file}")
        print("Using default or environment variables for PostgreSQL connection.")
        
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")
    print("Install with: pip install python-dotenv")

# PostgreSQL connection parameters for tests
PG_TEST_PARAMS = {
    "dbname": os.environ.get("HADES_TEST_DB_NAME", "hades_test"),
    "user": os.environ.get("HADES_TEST_DB_USER", "hades"),
    "password": os.environ.get("HADES_TEST_DB_PASSWORD", ""),  # Default empty for peer auth
    "host": os.environ.get("HADES_TEST_DB_HOST", "localhost"),
    "port": os.environ.get("HADES_TEST_DB_PORT", "5432")
}
