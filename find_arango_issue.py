"""
Utility script to debug ArangoDB URL scheme issues in Python-Arango
"""

import os
import sys
import logging
from arango import ArangoClient
from arango.http import DefaultHTTPClient
import urllib.parse
import inspect
import traceback

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_arango_url_handling():
    """Test ArangoDB URL handling to identify where the scheme is being lost"""
    
    # Get credentials from env
    host = os.environ.get("HADES_ARANGO_HOST", "localhost")
    port = os.environ.get("HADES_ARANGO_PORT", "8529")
    username = os.environ.get("HADES_ARANGO_USER", "root")
    password = os.environ.get("HADES_ARANGO_PASSWORD", "k$MfknQFhVB2wY7Z")
    db_name = os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    
    # Construct URL with scheme
    url = f"http://{host}:{port}"
    logger.info(f"Initial URL: {url}")
    
    try:
        # Create client
        client = ArangoClient(hosts=url)
        logger.info(f"Client created with URL: {url}")
        logger.info(f"Client hosts attribute: {client._hosts}")
        
        # Get HTTP client and examine its properties
        http_client = client._http
        logger.info(f"HTTP Client: {http_client.__class__.__name__}")
        
        # Examine HTTP client's host
        for attr_name in dir(http_client):
            if not attr_name.startswith('_') and not callable(getattr(http_client, attr_name)):
                try:
                    attr_value = getattr(http_client, attr_name)
                    logger.info(f"HTTP Client {attr_name}: {attr_value}")
                except:
                    pass
        
        # Try to connect
        sys_db = client.db("_system", username, password)
        logger.info("Connected to _system database")
        
        # Try to get database info
        logger.info(f"Trying to access database info")
        logger.info(f"Database URL: {sys_db.url}")
        
        # Check database endpoint components
        db_url_parts = urllib.parse.urlparse(sys_db.url)
        logger.info(f"Database URL parts: {db_url_parts}")
        
        # Try to get user database
        user_db = client.db(db_name, username, password)
        logger.info(f"Connected to user database {db_name}")
        logger.info(f"User database URL: {user_db.url}")
        
        # Try AQL query
        try:
            aql = "FOR doc IN _collections RETURN doc"
            logger.info(f"Executing AQL: {aql}")
            cursor = user_db.aql.execute(aql)
            result = list(cursor)
            logger.info(f"AQL result: {result}")
        except Exception as e:
            logger.error(f"AQL error: {e}")
            traceback.print_exc()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_arango_url_handling()
