#!/usr/bin/env python
"""
Script to create production API keys for HADES authentication.
This script will create API keys for production use and add them to the .env files.
"""
import os
import sys
from pathlib import Path

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
from hades.auth.pg_auth import create_api_key, get_db_connection

def check_hades_privileges():
    """Check if the hades PostgreSQL user has necessary privileges."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if user is superuser
            cursor.execute("""
                SELECT usesuper 
                FROM pg_user 
                WHERE usename = 'hades';
            """)
            result = cursor.fetchone()
            is_superuser = result["usesuper"] if result else False
            
            # Check database ownership
            cursor.execute("""
                SELECT 
                    d.datname as database_name,
                    pg_catalog.pg_get_userbyid(d.datdba) as owner
                FROM pg_catalog.pg_database d
                WHERE d.datname = 'hades_test';
            """)
            db_result = cursor.fetchone()
            is_db_owner = db_result["owner"] == "hades" if db_result else False
            
            # Check table privileges
            cursor.execute("""
                SELECT 
                    table_name, 
                    string_agg(privilege_type, ', ') as privileges
                FROM information_schema.table_privileges
                WHERE grantee = 'hades' AND table_schema = 'public'
                GROUP BY table_name;
            """)
            table_privileges = cursor.fetchall()
            
            print("\nHADES PostgreSQL User Privileges:")
            print(f"Superuser: {'Yes' if is_superuser else 'No'}")
            print(f"Database Owner (hades_test): {'Yes' if is_db_owner else 'No'}")
            
            if table_privileges:
                print("\nTable Privileges:")
                for priv in table_privileges:
                    print(f"  {priv['table_name']}: {priv['privileges']}")
            else:
                print("\nNo specific table privileges found.")
            
            # Recommend actions if needed
            if not is_superuser and not is_db_owner:
                print("\nRecommendation: Grant additional privileges to the hades user:")
                print("  sudo -u postgres psql -c \"ALTER USER hades WITH CREATEDB;\"")
                print("  sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE hades_test TO hades;\"")
                
            return is_superuser, is_db_owner, table_privileges
    except Exception as e:
        print(f"Error checking privileges: {e}")
        return False, False, []
    finally:
        if 'conn' in locals():
            conn.close()

def create_production_keys():
    """Create production API keys and add them to .env files."""
    # Create API keys
    service_key = create_api_key("hades_service")
    admin_key = create_api_key("hades_admin")
    
    print("\nCreated Production API Keys:")
    print(f"Service API Key: {service_key['api_key']}")
    print(f"Admin API Key: {admin_key['api_key']}")
    
    # Update .env and .env.test files
    env_files = [
        project_root / ".env",
        project_root / ".env.test"
    ]
    
    for env_file in env_files:
        if not env_file.exists():
            print(f"Creating new {env_file.name} file")
            env_content = ""
        else:
            print(f"Updating existing {env_file.name} file")
            env_content = env_file.read_text()
            
            # Remove existing API key entries if they exist
            new_lines = []
            for line in env_content.splitlines():
                if not line.startswith("HADES_SERVICE_API_KEY=") and not line.startswith("HADES_ADMIN_API_KEY="):
                    new_lines.append(line)
            env_content = "\n".join(new_lines)
            
            if env_content and not env_content.endswith("\n"):
                env_content += "\n"
        
        # Add API key entries
        env_content += f"\n# API Keys for authentication\n"
        env_content += f"HADES_SERVICE_API_KEY={service_key['api_key']}\n"
        env_content += f"HADES_ADMIN_API_KEY={admin_key['api_key']}\n"
        
        # Write updated content back to file
        env_file.write_text(env_content)
        print(f"Updated {env_file.name} with API keys")
    
    return service_key, admin_key

if __name__ == "__main__":
    print("Creating Production API Keys for HADES Authentication")
    
    # Check hades user privileges
    is_superuser, is_db_owner, _ = check_hades_privileges()
    
    if not is_superuser and not is_db_owner:
        proceed = input("\nThe hades user may not have all required privileges. Proceed anyway? (y/n): ")
        if proceed.lower() != 'y':
            print("Aborting. Please grant necessary privileges to the hades user.")
            sys.exit(1)
    
    # Create production keys
    service_key, admin_key = create_production_keys()
    
    print("\nAPI Keys have been added to .env and .env.test files.")
    print("You can now use these keys to authenticate to the HADES API.")
    print("\nExample usage with curl:")
    print(f"curl -H 'X-API-Key: {service_key['api_key']}' http://localhost:8000/api/v1/predict")
    print(f"curl -H 'X-API-Key: {admin_key['api_key']}' http://localhost:8000/api/v1/admin/status")
