#!/usr/bin/env python
"""
Verify PostgreSQL connection for HADES tests.
This script will check if we can connect to PostgreSQL with the hades user.
"""
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
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

# Try to import test environment variables
try:
    sys.path.insert(0, '.')
    from tests.pg_test_env import PG_TEST_PARAMS
except ImportError:
    print("Could not import PG_TEST_PARAMS from tests.pg_test_env")
    # Create connection parameters from environment variables
    PG_TEST_PARAMS = {
        "dbname": os.environ.get("HADES_TEST_DB_NAME", "hades_test"),
        "user": os.environ.get("HADES_TEST_DB_USER", "hades"),
        "password": os.environ.get("HADES_TEST_DB_PASSWORD", ""),
        "host": os.environ.get("HADES_TEST_DB_HOST", "localhost"),
        "port": os.environ.get("HADES_TEST_DB_PORT", "5432")
    }

def verify_connection():
    """Verify PostgreSQL connection with the hades user."""
    print(f"Verifying PostgreSQL connection with parameters:")
    print(f"  Host: {PG_TEST_PARAMS['host']}")
    print(f"  Port: {PG_TEST_PARAMS['port']}")
    print(f"  User: {PG_TEST_PARAMS['user']}")
    print(f"  Database: {PG_TEST_PARAMS['dbname']}")
    print(f"  Password: {'[provided]' if PG_TEST_PARAMS['password'] else '[not provided]'}")
    
    try:
        # Try to connect to the database
        conn = psycopg2.connect(**PG_TEST_PARAMS, cursor_factory=RealDictCursor)
        
        # Get PostgreSQL version
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()['version']
            print(f"\nSuccessfully connected to PostgreSQL!")
            print(f"PostgreSQL version: {version}")
            
            # Check if the required tables exist
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'api_keys'
                );
            """)
            api_keys_exists = cursor.fetchone()['exists']
            
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'rate_limits'
                );
            """)
            rate_limits_exists = cursor.fetchone()['exists']
            
            print(f"\nRequired tables:")
            print(f"  api_keys: {'EXISTS' if api_keys_exists else 'MISSING'}")
            print(f"  rate_limits: {'EXISTS' if rate_limits_exists else 'MISSING'}")
            
            if not api_keys_exists or not rate_limits_exists:
                print("\nSome required tables are missing. Please run the setup script:")
                print("  python tests/setup_pg_test_db.py")
        
        conn.close()
        return True
    except Exception as e:
        print(f"\nError connecting to PostgreSQL: {e}")
        print("\nPlease check your PostgreSQL installation and credentials.")
        print("You may need to run the setup script or create the hades user:")
        print("  sudo -u postgres createuser --createdb --pwprompt hades")
        print("  sudo -u postgres createdb -O hades hades_test")
        return False

if __name__ == "__main__":
    if verify_connection():
        sys.exit(0)
    else:
        sys.exit(1)
