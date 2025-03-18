#!/usr/bin/env python
"""
Test script for ArangoDB connection.

This script directly tests the DirectArangoAPI connection without going through the MCP server.
"""

import os
import sys
import json
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import HADES modules
from src.db.arangodb_connection_fix_v2 import DirectArangoAPI, get_client
from src.utils.logger import get_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

def test_direct_arango_api():
    """Test the DirectArangoAPI connection."""
    # Load environment variables
    load_dotenv()
    
    # Get ArangoDB credentials from environment
    arango_host = os.environ.get("HADES_ARANGO_HOST", "localhost")
    arango_port = os.environ.get("HADES_ARANGO_PORT", "8529")
    arango_user = os.environ.get("HADES_ARANGO_USER", "hades")
    arango_password = os.environ.get("HADES_ARANGO_PASSWORD", "LVlX5fshvf0H24cWQNHjm41S")
    arango_db_name = os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    
    # Log loaded environment variables
    logger.info(f"ArangoDB Host: {arango_host}")
    logger.info(f"ArangoDB Port: {arango_port}")
    logger.info(f"ArangoDB User: {arango_user}")
    logger.info(f"ArangoDB Password: {'*' * len(arango_password) if arango_password else 'Not Set'}")
    logger.info(f"ArangoDB Database: {arango_db_name}")
    
    # Create DirectArangoAPI instance
    try:
        logger.info("Creating DirectArangoAPI instance...")
        api = DirectArangoAPI(
            host=arango_host,
            port=arango_port,
            username=arango_user,
            password=arango_password,
            database=arango_db_name
        )
        
        logger.info(f"DirectArangoAPI initialized with base URL: {api.base_url}")
        
        # Test a simple query
        logger.info("Testing simple query...")
        result = api.execute_query("RETURN 1")
        
        logger.info(f"Query result: {result}")
        
        if result.get("success", False):
            logger.info("Query succeeded!")
        else:
            logger.error(f"Query failed: {result.get('error', 'Unknown error')}")
        
        # Test collections query
        logger.info("Testing collections query...")
        result = api.execute_query("FOR c IN _collections RETURN c.name")
        
        if result.get("success", False):
            logger.info("Collections query succeeded!")
            logger.info(f"Collections: {result.get('result', [])}")
        else:
            logger.error(f"Collections query failed: {result.get('error', 'Unknown error')}")
            
        # Test entities query
        logger.info("Testing entities query...")
        result = api.execute_query("FOR e IN entities LIMIT 5 RETURN e.name")
        
        if result.get("success", False):
            logger.info("Entities query succeeded!")
            logger.info(f"Entity names: {result.get('result', [])}")
        else:
            logger.error(f"Entities query failed: {result.get('error', 'Unknown error')}")
            
        # Test path retrieval query
        logger.info("Testing path retrieval query...")
        query = "ArangoDB"  # Entity to search from
        aql_query = f"""
        FOR v, e, p IN 1..5 OUTBOUND 'entities/{query}' edges
            LIMIT 5
            RETURN {{
                "path": CONCAT_SEPARATOR(' -> ', p.vertices[*].name),
                "vertices": p.vertices[*].name,
                "score": LENGTH(p.vertices)
            }}
        """
        
        result = api.execute_query(aql_query)
        
        if result.get("success", False):
            logger.info("Path retrieval query succeeded!")
            paths = result.get("result", [])
            if paths:
                logger.info(f"Found {len(paths)} paths:")
                for i, path in enumerate(paths):
                    logger.info(f"  Path {i+1}: {path.get('path', 'Unknown path')}")
            else:
                logger.info("No paths found.")
        else:
            logger.error(f"Path retrieval query failed: {result.get('error', 'Unknown error')}")
            
        return True
    except Exception as e:
        logger.error(f"Error testing DirectArangoAPI: {e}")
        return False

def test_arango_client():
    """Test the ArangoClient connection."""
    # Load environment variables
    load_dotenv()
    
    # Get ArangoDB credentials from environment
    arango_host = os.environ.get("HADES_ARANGO_HOST", "localhost")
    arango_port = os.environ.get("HADES_ARANGO_PORT", "8529")
    arango_user = os.environ.get("HADES_ARANGO_USER", "hades")
    arango_password = os.environ.get("HADES_ARANGO_PASSWORD", "LVlX5fshvf0H24cWQNHjm41S")
    arango_db_name = os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    
    try:
        logger.info("Testing ArangoClient connection...")
        client = get_client(
            host=arango_host,
            port=arango_port
        )
        
        # Connect to system database
        logger.info("Connecting to _system database...")
        sys_db = client.db("_system", arango_user, arango_password)
        
        # List databases
        logger.info("Listing databases...")
        databases = sys_db.databases()
        logger.info(f"Databases: {databases}")
        
        # Check if our database exists
        if arango_db_name in databases:
            logger.info(f"Database '{arango_db_name}' exists!")
            
            # Connect to our database
            logger.info(f"Connecting to '{arango_db_name}' database...")
            db = client.db(arango_db_name, arango_user, arango_password)
            
            # List collections
            logger.info("Listing collections...")
            collections = db.collections()
            collection_names = [c["name"] for c in collections]
            logger.info(f"Collections: {collection_names}")
            
            # Check for entities collection
            if "entities" in collection_names:
                logger.info("'entities' collection exists!")
                
                # Get entity count
                logger.info("Getting entity count...")
                cursor = db.aql.execute("RETURN LENGTH(entities)")
                count = next(cursor)
                logger.info(f"Entity count: {count}")
                
                # Get a few entity names
                logger.info("Getting entity names...")
                cursor = db.aql.execute("FOR e IN entities LIMIT 5 RETURN e.name")
                names = [doc for doc in cursor]
                logger.info(f"Entity names: {names}")
                
                # Test path retrieval
                logger.info("Testing path retrieval...")
                entity_name = "ArangoDB"
                cursor = db.aql.execute(f"""
                FOR v, e, p IN 1..5 OUTBOUND 'entities/{entity_name}' edges
                    LIMIT 5
                    RETURN {{
                        "path": CONCAT_SEPARATOR(' -> ', p.vertices[*].name),
                        "vertices": p.vertices[*].name,
                        "score": LENGTH(p.vertices)
                    }}
                """)
                
                paths = [doc for doc in cursor]
                if paths:
                    logger.info(f"Found {len(paths)} paths:")
                    for i, path in enumerate(paths):
                        logger.info(f"  Path {i+1}: {path.get('path', 'Unknown path')}")
                else:
                    logger.info("No paths found.")
            else:
                logger.warning("'entities' collection does not exist!")
        else:
            logger.warning(f"Database '{arango_db_name}' does not exist!")
            
        return True
    except Exception as e:
        logger.error(f"Error testing ArangoClient: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing DirectArangoAPI ===")
    test_direct_arango_api()
    
    print("\n=== Testing ArangoClient ===")
    test_arango_client()
