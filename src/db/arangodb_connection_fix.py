"""
ArangoDB Connection Fix

This module provides a patched version of the ArangoDB connection that properly
handles URL scheme issues in the Python-Arango library.
"""

import os
import logging
import requests
from urllib.parse import urlparse
# ArangoDB imports
from arango import ArangoClient, AQLQueryExecuteError
from arango.collection import StandardCollection
from arango.database import StandardDatabase
from arango.exceptions import ServerConnectionError

# Configure logger
logger = logging.getLogger(__name__)

def make_fully_qualified_url(url):
    """Ensure URL has proper scheme.
    
    Args:
        url: URL to check/fix
        
    Returns:
        URL with http:// scheme if not already present
    """
    if not url.startswith('http://') and not url.startswith('https://'):
        return f"http://{url}"
    return url

def get_client(host=None, port=None):
    """Get a properly configured ArangoDB client.
    
    Args:
        host: ArangoDB host (default: from environment)
        port: ArangoDB port (default: from environment)
        
    Returns:
        ArangoClient instance with proper URL configuration
    """
    # Get connection details from parameters or environment
    arango_host = host or os.environ.get("HADES_ARANGO_HOST", "localhost")
    arango_port = port or os.environ.get("HADES_ARANGO_PORT", "8529")
    
    # Ensure URL has scheme
    hosts = make_fully_qualified_url(f"{arango_host}:{arango_port}")
    
    logger.info(f"Creating ArangoDB client for URL: {hosts}")
    
    # Create client with explicit protocol in URL
    return ArangoClient(hosts=hosts)
        
def get_database(database_name=None, username=None, password=None, create_if_not_exists=True):
    """Get a properly configured ArangoDB database connection.
    
    Args:
        database_name: Name of the database to connect to (default: from environment)
        username: ArangoDB username (default: from environment)
        password: ArangoDB password (default: from environment)
        create_if_not_exists: Create the database if it doesn't exist
        
    Returns:
        An ArangoDB database connection
    """
    # Get database name from parameter or environment
    db_name = database_name or os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    arango_user = username or os.environ.get("HADES_ARANGO_USER", "root")
    arango_password = password or os.environ.get("HADES_ARANGO_PASSWORD", "k$MfknQFhVB2wY7Z")
    
    # Get client
    client = get_client()
    
    try:
        # Try to connect to the system database first
        sys_db = client.db("_system", arango_user, arango_password)
        logger.info("Connected to _system database successfully")
        
        # Check if our target database exists
        if not sys_db.has_database(db_name) and create_if_not_exists:
            logger.info(f"Database {db_name} does not exist. Creating it.")
            sys_db.create_database(db_name)
            logger.info(f"Created database {db_name}")
            
        # Connect to the user database
        db = client.db(db_name, arango_user, arango_password)
        logger.info(f"Connected to database {db_name} successfully")
        return db
        
    except Exception as e:
        logger.error(f"Error connecting to ArangoDB: {e}")
        raise
    
# Create a simple direct API wrapper for ArangoDB as a fallback
class DirectArangoAPI:
    """Direct API wrapper for ArangoDB that avoids using the Python-Arango library."""
    
    def __init__(self, host=None, port=None, username=None, password=None, database=None):
        """Initialize the direct API wrapper.
        
        Args:
            host: ArangoDB host (default: from environment)
            port: ArangoDB port (default: from environment)
            username: ArangoDB username (default: from environment)
            password: ArangoDB password (default: from environment)
            database: ArangoDB database name (default: from environment)
        """
        # Get credentials from parameters or environment
        arango_host = host or os.environ.get("HADES_ARANGO_HOST", "localhost")
        arango_port = port or os.environ.get("HADES_ARANGO_PORT", "8529")
        self.username = username or os.environ.get("HADES_ARANGO_USER", "root")
        self.password = password or os.environ.get("HADES_ARANGO_PASSWORD", "k$MfknQFhVB2wY7Z")
        self.database = database or os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
        
        # Ensure URL has a scheme
        if not arango_host.startswith("http://") and not arango_host.startswith("https://"):
            self.base_url = f"http://{arango_host}:{arango_port}"
        else:
            self.base_url = f"{arango_host}:{arango_port}"
        
        # Set up auth for requests
        self.auth = (self.username, self.password)
        
        logger.info(f"DirectArangoAPI initialized with base URL: {self.base_url}")
    
    def execute_query(self, query, bind_vars=None):
        """Execute an AQL query directly via the REST API.
        
        Args:
            query: AQL query to execute
            bind_vars: Query parameters
            
        Returns:
            Query results
        """
        bind_vars = bind_vars or {}
        
        # Construct API endpoint URL
        api_url = f"{self.base_url}/_db/{self.database}/_api/cursor"
        logger.debug(f"Executing query at: {api_url}")
        
        # Prepare payload
        payload = {
            "query": query,
            "bindVars": bind_vars,
            "batchSize": 100
        }
        
        try:
            # Execute query
            response = requests.post(
                api_url,
                json=payload,
                auth=self.auth,
                headers={"Content-Type": "application/json"}
            )
            
            # Handle response
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "result": result.get("result", []),
                    "count": result.get("count", 0),
                    "has_more": result.get("hasMore", False)
                }
            else:
                logger.error(f"ArangoDB query failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"ArangoDB query failed: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.exception(f"Error executing ArangoDB query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def get_collections(self):
        """Get a list of collections in the database.
        
        Returns:
            List of collections
        """
        api_url = f"{self.base_url}/_db/{self.database}/_api/collection"
        
        try:
            response = requests.get(
                api_url,
                auth=self.auth
            )
            
            if response.status_code == 200:
                return response.json().get("result", [])
            else:
                logger.error(f"Failed to get collections: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.exception(f"Error getting collections: {e}")
            return []
            
    def create_collection(self, name, is_edge=False):
        """Create a collection in the database.
        
        Args:
            name: Collection name
            is_edge: Whether this is an edge collection
            
        Returns:
            True if successful, False otherwise
        """
        api_url = f"{self.base_url}/_db/{self.database}/_api/collection"
        
        collection_type = 3 if is_edge else 2  # 3 for edge, 2 for document
        payload = {
            "name": name,
            "type": collection_type
        }
        
        try:
            response = requests.post(
                api_url,
                json=payload,
                auth=self.auth
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Created collection {name}")
                return True
            else:
                # If collection already exists, that's fine
                if "duplicate name" in response.text:
                    logger.info(f"Collection {name} already exists")
                    return True
                    
                logger.error(f"Failed to create collection: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.exception(f"Error creating collection: {e}")
            return False
