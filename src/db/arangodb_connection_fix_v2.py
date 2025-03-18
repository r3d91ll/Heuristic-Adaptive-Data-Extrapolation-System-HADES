"""
ArangoDB Connection Fix (Version 2)

This module provides a properly configured connection to ArangoDB that resolves 
URL scheme issues in the Python-Arango library. Based on official ArangoDB documentation.
"""

import os
import logging
import requests
from urllib.parse import urlparse
from arango import ArangoClient

# Configure logger
logger = logging.getLogger(__name__)

def get_client(url=None, host=None, port=None):
    """Get a properly configured ArangoDB client.
    
    Args:
        url: Full ArangoDB URL including scheme, host and port (default: from environment)
        host: ArangoDB host, used if url is not provided (default: from environment)
        port: ArangoDB port, used if url is not provided (default: from environment)
        
    Returns:
        ArangoClient instance with proper URL configuration
    """
    # Try to load .env file if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, will use environment variables as-is
    
    # Prioritize using the full URL if provided either directly or from environment
    if url:
        hosts = url
        logger.info(f"Connecting to ArangoDB using provided URL: {hosts}")
    elif os.environ.get("HADES_ARANGO_URL"):
        hosts = os.environ.get("HADES_ARANGO_URL")
        logger.info(f"Connecting to ArangoDB using URL from environment: {hosts}")
    else:
        # Get connection details from parameters or environment
        arango_host = host or os.environ.get("HADES_ARANGO_HOST", "localhost")
        arango_port = port or os.environ.get("HADES_ARANGO_PORT", "8529")
        
        logger.info(f"Connecting to ArangoDB host: {arango_host}, port: {arango_port}")
        
        # Parse the URL to handle different cases correctly
        parsed_url = urlparse(arango_host)
    
    # Ensure URL has scheme
    if not parsed_url.scheme:
        # No scheme, add http:// and port
        hosts = f"http://{arango_host}:{arango_port}"
        logger.info(f"Added scheme to host: {hosts}")
    else:
        # URL already has a scheme
        if parsed_url.port:
            # URL already has a port
            hosts = arango_host
            logger.info(f"Using host with existing scheme and port: {hosts}")
        else:
            # URL has scheme but no port
            hosts = f"{arango_host}:{arango_port}"
            logger.info(f"Added port to host with scheme: {hosts}")
    
    # Double-check the URL has a scheme
    parsed_hosts = urlparse(hosts)
    if not parsed_hosts.scheme:
        logger.warning(f"Hosts URL still missing scheme: {hosts}")
        hosts = f"http://{hosts}"
        logger.info(f"Forced http:// scheme, final hosts: {hosts}")
    
    logger.info(f"Creating ArangoDB client with hosts: {hosts}")
    
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
    # Try to load .env file if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv not installed, will use environment variables as-is
        
    # Get database name from parameter or environment
    db_name = database_name or os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    arango_user = username or os.environ.get("HADES_ARANGO_USER", "hades")
    arango_password = password or os.environ.get("HADES_ARANGO_PASSWORD", "LVlX5fshvf0H24cWQNHjm41S")
    
    logger.debug(f"Connecting to ArangoDB database {db_name} as user {arango_user}")
    
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

class DirectArangoAPI:
    """Direct API wrapper for ArangoDB that avoids URL scheme issues."""
    
    def __init__(self, url=None, host=None, port=None, username=None, password=None, database=None):
        """Initialize the direct API wrapper.
        
        Args:
            url: Full ArangoDB URL including scheme, host and port (default: from environment)
            host: ArangoDB host, used if url is not provided (default: from environment)
            port: ArangoDB port, used if url is not provided (default: from environment)
            username: ArangoDB username (default: from environment)
            password: ArangoDB password (default: from environment)
            database: ArangoDB database name (default: from environment)
        """
        # Load dotenv file if available to ensure environment variables are set
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv not installed, will use environment variables as-is
        
        # Get credentials from parameters or environment
        self.username = username or os.environ.get("HADES_ARANGO_USER", "hades")
        self.password = password or os.environ.get("HADES_ARANGO_PASSWORD", "LVlX5fshvf0H24cWQNHjm41S")
        self.database = database or os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
        
        logger.debug(f"DirectArangoAPI initializing with username: {self.username}, database: {self.database}")
        
        # Prioritize using the full URL if provided either directly or from environment
        if url:
            # URL provided directly as parameter
            self.base_url = url
            logger.info(f"Using provided URL: {self.base_url}")
        elif os.environ.get("HADES_ARANGO_URL"):
            # URL provided in environment
            self.base_url = os.environ.get("HADES_ARANGO_URL")
            logger.info(f"Using URL from environment: {self.base_url}")
        else:
            # No URL provided, construct from host and port
            arango_host = host or os.environ.get("HADES_ARANGO_HOST", "localhost")
            arango_port = port or os.environ.get("HADES_ARANGO_PORT", "8529")
            
            # Parse the URL to handle different cases correctly
            parsed_url = urlparse(arango_host)
            
            # Ensure URL has a scheme
            if not parsed_url.scheme:
                # No scheme, add http:// and port
                self.base_url = f"http://{arango_host}:{arango_port}"
                logger.info(f"Constructed URL with scheme: {self.base_url}")
            else:
                # URL already has a scheme
                if parsed_url.port:
                    # URL already has port specified
                    self.base_url = arango_host
                    logger.info(f"Using host with existing scheme and port: {self.base_url}")
                else:
                    # URL has scheme but no port
                    self.base_url = f"{arango_host}:{arango_port}"
                    logger.info(f"Added port to URL with scheme: {self.base_url}")
                
        # Double-check that base_url has a scheme
        parsed_base_url = urlparse(self.base_url)
        if not parsed_base_url.scheme:
            logger.warning(f"Base URL still missing scheme: {self.base_url}")
            self.base_url = f"http://{self.base_url}"
            logger.info(f"Forced http:// scheme, final base_url: {self.base_url}")
        
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
        
        # Log base URL for debugging
        logger.info(f"Base URL before building API endpoint: {self.base_url}")
        
        # Ensure base_url has a scheme
        parsed_base_url = urlparse(self.base_url)
        if not parsed_base_url.scheme:
            self.base_url = f"http://{self.base_url}"
            logger.info(f"Fixed base URL by adding scheme: {self.base_url}")
            
        # Construct API endpoint URL
        api_url = f"{self.base_url}/_db/{self.database}/_api/cursor"
        
        # Double-check the URL has a scheme
        parsed_url = urlparse(api_url)
        if not parsed_url.scheme:
            logger.warning(f"API URL missing scheme: {api_url}")
            api_url = f"http://{api_url}"
            logger.info(f"Fixed API URL by adding scheme: {api_url}")
            
        logger.info(f"Executing query at final URL: {api_url}")
        
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
            if response.status_code in [200, 201]:
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
