#!/usr/bin/env python3
"""
HADES Native Database Connection Tests.
This script tests connections to both PostgreSQL and ArangoDB on a bare metal installation.
"""
import os
import sys
import psycopg2
from arango import ArangoClient, ArangoError

def test_postgresql():
    """Test connection to PostgreSQL."""
    print("\nTesting PostgreSQL Connection...")
    
    # Get connection parameters from environment variables
    host = os.environ.get("HADES_PG_HOST", "localhost")
    port = os.environ.get("HADES_PG_PORT", "5432")
    user = os.environ.get("HADES_PG_USER", "hades")
    password = os.environ.get("HADES_PG_PASSWORD", "o$n^3W%QD0HGWxH!")
    database = os.environ.get("HADES_PG_DATABASE", "hades_test")
    
    print(f"Connecting to PostgreSQL at {host}:{port} as {user}...")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute a test query
        cur.execute("SELECT version();")
        
        # Fetch results
        version = cur.fetchone()[0]
        print(f"PostgreSQL version: {version}")
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        print("PostgreSQL connection test succeeded.")
        return True
        
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return False

def test_arangodb():
    """Test connection to ArangoDB."""
    print("\nTesting ArangoDB Connection...")
    
    # Get connection parameters from environment variables
    host = os.environ.get("HADES_ARANGO_HOST", "localhost")
    port = os.environ.get("HADES_ARANGO_PORT", "8529")
    
    # Ensure host has a scheme
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    
    # Ensure port is in the host URL
    if f":{port}" not in host:
        host = f"{host}:{port}"
    
    user = os.environ.get("HADES_ARANGO_USER", "hades")
    password = os.environ.get("HADES_ARANGO_PASSWORD", "o$n^3W%QD0HGWxH!")
    database = os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    
    print(f"Connecting to ArangoDB at {host} as {user}...")
    
    try:
        # Connect to ArangoDB
        client = ArangoClient(hosts=host)
        
        # Connect to the database
        db = client.db(
            database,
            username=user,
            password=password
        )
        
        # Get database version
        version = db.version()
        print(f"ArangoDB version: {version}")
        
        # Get list of collections to verify database access
        collections = db.collections()
        print(f"ArangoDB collections: {[c['name'] for c in collections]}")
        
        print("ArangoDB connection test succeeded.")
        return True
        
    except Exception as e:
        print(f"Error connecting to ArangoDB: {e}")
        return False

def main():
    """Main function."""
    print("HADES Native Database Connection Tests")
    print("=====================================")
    
    pg_success = test_postgresql()
    arango_success = test_arangodb()
    
    print("\nConnection Test Results:")
    print(f"PostgreSQL: {'SUCCESS' if pg_success else 'FAILED'}")
    print(f"ArangoDB:   {'SUCCESS' if arango_success else 'FAILED'}")
    
    if pg_success and arango_success:
        print("\nAll database connection tests succeeded!")
        return 0
    else:
        print("\nSome database connection tests failed. Check the logs above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
