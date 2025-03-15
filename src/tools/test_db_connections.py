#!/usr/bin/env python3
"""
Test database connections for HADES.
"""
import os
import sys
from datetime import datetime

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("Error: psycopg2-binary package not installed.")
    print("Install it with: pip install psycopg2-binary")
    sys.exit(1)

try:
    from arango import ArangoClient
except ImportError:
    print("Error: python-arango package not installed.")
    print("Install it with: pip install python-arango")
    sys.exit(1)

def test_postgresql():
    """Test PostgreSQL connection."""
    print("\n--- Testing PostgreSQL Connection ---")
    
    host = os.environ.get("HADES_PG_HOST", "localhost")
    port = os.environ.get("HADES_PG_PORT", "5432")
    user = os.environ.get("HADES_PG_USER", "hades")
    password = os.environ.get("HADES_PG_PASSWORD", "hades_password")
    database = os.environ.get("HADES_PG_DATABASE", "hades_auth")
    
    print(f"Connecting to PostgreSQL at {host}:{port}, database: {database}, user: {user}")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=database
        )
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"Connected successfully to PostgreSQL")
            print(f"PostgreSQL version: {version}")
            
            # Create test table
            print("Creating test table...")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS connection_test (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
            """)
            
            # Insert test data
            test_message = f"Connection test at {datetime.now().isoformat()}"
            cursor.execute(
                "INSERT INTO connection_test (message, created_at) VALUES (%s, %s) RETURNING id",
                (test_message, datetime.now())
            )
            test_id = cursor.fetchone()[0]
            
            # Retrieve test data
            cursor.execute("SELECT message FROM connection_test WHERE id = %s", (test_id,))
            retrieved_message = cursor.fetchone()[0]
            
            print(f"Test data written and retrieved successfully: '{retrieved_message}'")
            
            # Clean up
            cursor.execute("DROP TABLE connection_test")
            
        conn.commit()
        conn.close()
        print("PostgreSQL connection test completed successfully!")
        return True
    
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return False

def test_arangodb():
    """Test ArangoDB connection."""
    print("\n--- Testing ArangoDB Connection ---")
    
    host = os.environ.get("HADES_ARANGO_HOST", "localhost")
    port = os.environ.get("HADES_ARANGO_PORT", "8529")
    user = os.environ.get("HADES_ARANGO_USER", "hades")
    password = os.environ.get("HADES_ARANGO_PASSWORD", "hades_password")
    database = os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    
    print(f"Connecting to ArangoDB at {host}:{port}, database: {database}, user: {user}")
    
    try:
        # Connect to ArangoDB
        client = ArangoClient(hosts=f"http://{host}:{port}")
        db = client.db(database, username=user, password=password)
        
        # Get version information
        version = db.version()
        print(f"Connected successfully to ArangoDB")
        print(f"ArangoDB version: {version}")
        
        # We're already connected to the database, so we can proceed with testing
        
        # Create test collection
        collection_name = "connection_test"
        if db.has_collection(collection_name):
            test_collection = db.collection(collection_name)
        else:
            test_collection = db.create_collection(collection_name)
        print(f"Using collection: {collection_name}")
        
        # Insert test document
        test_doc = {
            "message": f"Connection test at {datetime.now().isoformat()}",
            "created_at": datetime.now().isoformat()
        }
        meta = test_collection.insert(test_doc)
        doc_id = meta["_id"]
        
        # Retrieve test document
        retrieved_doc = test_collection.get(doc_id)
        print(f"Test document written and retrieved successfully: '{retrieved_doc['message']}'")
        
        # Clean up
        test_collection.delete(doc_id)
        db.delete_collection(collection_name)
        
        print("ArangoDB connection test completed successfully!")
        return True
    
    except Exception as e:
        print(f"Error connecting to ArangoDB: {e}")
        return False

def main():
    """Main function."""
    print("HADES Database Connection Tests")
    print("===============================")
    
    pg_success = test_postgresql()
    arango_success = test_arangodb()
    
    print("\n--- Test Summary ---")
    print(f"PostgreSQL: {'SUCCESS' if pg_success else 'FAILED'}")
    print(f"ArangoDB: {'SUCCESS' if arango_success else 'FAILED'}")
    
    if pg_success and arango_success:
        print("\nAll database connection tests passed successfully!")
        return 0
    else:
        print("\nSome database connection tests failed. Check the logs above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
