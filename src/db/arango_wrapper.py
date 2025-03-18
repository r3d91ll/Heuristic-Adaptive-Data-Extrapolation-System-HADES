"""
ArangoDB Connection Wrapper Module

This module provides a wrapper for ArangoDB connections to ensure proper URL handling
and authentication throughout all operations.
"""

import logging
import requests
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urlunparse
import json
import os

# Configure logger
logger = logging.getLogger(__name__)

class ArangoWrapper:
    """
    A wrapper for ArangoDB connections that ensures proper URL handling and authentication.
    This class provides direct REST API access to ArangoDB to bypass URL scheme issues
    in the Python-Arango library.
    """
    
    def __init__(self, host: str, username: str, password: str, database: str):
        """
        Initialize the ArangoWrapper.
        
        Args:
            host: The ArangoDB host (with or without scheme)
            username: The username for authentication
            password: The password for authentication
            database: The database to connect to
        """
        # Ensure host has proper scheme
        parsed = urlparse(host)
        if not parsed.scheme:
            parsed = parsed._replace(scheme='http')
        # Store full endpoint
        self.endpoint = urlunparse(parsed)
        self.username = username
        self.password = password
        self.database = database
        
        # Auth parameters
        self.auth = (username, password)
        
        logger.info(f"Initialized ArangoWrapper with endpoint: {self.endpoint}")
        
    def execute_query(self, query: str, bind_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute an AQL query via the REST API.
        
        Args:
            query: The AQL query to execute
            bind_vars: Query parameters
            
        Returns:
            Query results
        """
        bind_vars = bind_vars or {}
        
        # Construct API endpoint URL with scheme
        api_url = f"{self.endpoint}/_db/{self.database}/_api/cursor"
        logger.info(f"Executing query at: {api_url}")
        
        # Prepare payload
        payload = {
            "query": query,
            "bindVars": bind_vars,
            "batchSize": 100,
            "cache": False
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
                "error": f"Error executing ArangoDB query: {e}"
            }
            
    def get_collections(self) -> List[Dict[str, Any]]:
        """
        Get a list of all collections in the database.
        
        Returns:
            List of collections
        """
        api_url = f"{self.endpoint}/_db/{self.database}/_api/collection"
        
        try:
            response = requests.get(
                api_url,
                auth=self.auth,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json().get("result", [])
            else:
                logger.error(f"Failed to get collections: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.exception(f"Error getting collections: {e}")
            return []
            
    def create_collection(self, name: str, is_edge: bool = False) -> bool:
        """
        Create a new collection in the database.
        
        Args:
            name: The name of the collection
            is_edge: Whether to create an edge collection
            
        Returns:
            True if successful, False otherwise
        """
        api_url = f"{self.endpoint}/_db/{self.database}/_api/collection"
        
        collection_type = 3 if is_edge else 2  # 3 for edge, 2 for document
        payload = {
            "name": name,
            "type": collection_type
        }
        
        try:
            response = requests.post(
                api_url,
                json=payload,
                auth=self.auth,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Created collection {name}")
                return True
            else:
                # If the collection already exists, return True
                if "duplicate name" in response.text:
                    logger.info(f"Collection {name} already exists")
                    return True
                    
                logger.error(f"Failed to create collection: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.exception(f"Error creating collection: {e}")
            return False

def get_arango_wrapper(host=None, username=None, password=None, database=None) -> ArangoWrapper:
    """
    Get an ArangoWrapper instance configured with environment variables.
    
    Returns:
        An ArangoWrapper instance
    """
    # Get ArangoDB credentials from environment or parameters
    arango_host = host or os.environ.get("HADES_ARANGO_HOST", "localhost")
    arango_port = os.environ.get("HADES_ARANGO_PORT", "8529")
    arango_user = username or os.environ.get("HADES_ARANGO_USER", "root")
    arango_password = password or os.environ.get("HADES_ARANGO_PASSWORD", "k$MfknQFhVB2wY7Z")
    arango_db_name = database or os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    
    # Construct URL with scheme, ensuring it has a proper protocol
    if not arango_host.startswith("http://") and not arango_host.startswith("https://"):
        arango_url = f"http://{arango_host}:{arango_port}"
    else:
        # If host already includes protocol, use it as is
        arango_url = f"{arango_host}:{arango_port}"
    
    return ArangoWrapper(
        host=arango_url,
        username=arango_user,
        password=arango_password,
        database=arango_db_name
    )
