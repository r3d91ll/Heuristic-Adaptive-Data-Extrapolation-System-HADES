#!/usr/bin/env python
"""
Setup script for PostgreSQL hades database.
This script will create the hades user and test database using the credentials from .env.test.
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables only.")

def get_admin_connection_params():
    """Get PostgreSQL admin connection parameters."""
    # Default connection parameters for admin connection
    params = {
        "dbname": "postgres",  # Connect to default postgres database first
        "user": "postgres",    # Use postgres admin user
        "password": "",        # Empty password for peer authentication
        "host": "localhost",
        "port": "5432"
    }
    
    print(f"Using PostgreSQL admin connection parameters:")
    print(f"  Host: {params['host']}")
    print(f"  Port: {params['port']}")
    print(f"  User: {params['user']}")
    print(f"  Database: {params['dbname']}")
    
    return params

def get_hades_credentials():
    """Get hades user credentials from environment variables."""
    hades_user = os.environ.get("HADES_TEST_DB_USER", "hades")
    hades_password = os.environ.get("HADES_TEST_DB_PASSWORD", "")
    hades_db = os.environ.get("HADES_TEST_DB_NAME", "hades_test")
    
    print(f"Hades credentials:")
    print(f"  User: {hades_user}")
    print(f"  Database: {hades_db}")
    print(f"  Password: {'[provided]' if hades_password else '[not provided]'}")
    
    return hades_user, hades_password, hades_db

def setup_hades_user_and_db():
    """Set up the hades user and database."""
    admin_params = get_admin_connection_params()
    hades_user, hades_password, hades_db = get_hades_credentials()
    
    conn = None
    try:
        # Connect to PostgreSQL server with admin privileges
        print(f"Connecting to PostgreSQL server as admin...")
        conn = psycopg2.connect(**admin_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create a cursor
        cur = conn.cursor()
        
        # Check if hades user exists
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (hades_user,))
        user_exists = cur.fetchone() is not None
        
        if user_exists:
            print(f"User '{hades_user}' already exists. Updating password...")
            # Update password for existing user
            cur.execute(f"ALTER USER {hades_user} WITH PASSWORD %s", (hades_password,))
        else:
            print(f"Creating user '{hades_user}'...")
            # Create hades user with password
            cur.execute(f"CREATE USER {hades_user} WITH PASSWORD %s", (hades_password,))
            # Grant privileges
            cur.execute(f"ALTER USER {hades_user} CREATEDB")
        
        # Check if hades_test database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (hades_db,))
        db_exists = cur.fetchone() is not None
        
        if db_exists:
            print(f"Database '{hades_db}' already exists.")
        else:
            print(f"Creating database '{hades_db}'...")
            # Create hades_test database owned by hades user
            cur.execute(f"CREATE DATABASE {hades_db} OWNER {hades_user}")
        
        # Close cursor
        cur.close()
        
        # Connect to the hades_test database to create tables
        print(f"Connecting to '{hades_db}' database to set up tables...")
        db_params = admin_params.copy()
        db_params["dbname"] = hades_db
        
        db_conn = psycopg2.connect(**db_params)
        db_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        db_cur = db_conn.cursor()
        
        # Create tables for authentication
        print("Creating tables for authentication...")
        db_cur.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id VARCHAR(64) PRIMARY KEY,
                key_hash VARCHAR(128) NOT NULL,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP WITH TIME ZONE
            )
        """)
        
        db_cur.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                key_id VARCHAR(64) REFERENCES api_keys(key_id),
                endpoint VARCHAR(255) NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                window_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (key_id, endpoint)
            )
        """)
        
        # Grant privileges to hades user
        db_cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {hades_user}")
        
        # Close database connection
        db_cur.close()
        db_conn.close()
        
        print(f"\nPostgreSQL setup completed successfully!")
        print(f"User '{hades_user}' and database '{hades_db}' are ready for testing.")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if setup_hades_user_and_db():
        sys.exit(0)
    else:
        sys.exit(1)
