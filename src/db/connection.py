from arango import ArangoClient, ArangoError
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class DBConnection:
    """
    Database connection manager for HADES.
    
    This module handles the connection to the ArangoDB database.
    """

    def __init__(self, db_name: str = "hades_db"):
        """Initialize the DBConnection module."""
        logger.info("Initializing DBConnection module")
        self.client = ArangoClient()
        self.db_name = db_name
        self.db = None
    
    def connect(self, host: str = "http://localhost:8529", username: str = "root", password: str = "") -> bool:
        """
        Connect to the ArangoDB database.
        
        Args:
            host: The host URL of the ArangoDB server
            username: The username for authentication
            password: The password for authentication
            
        Returns:
            True if connection is successful, False otherwise
        """
        logger.info(f"Connecting to ArangoDB at {host}")
        
        try:
            self.client = ArangoClient()
            self.db = self.client.db(self.db_name, username=username, password=password, verify=True)
            logger.info("Successfully connected to the database")
            return True
        
        except ArangoError as e:
            logger.error(f"Database connection failed: {e}")
            return False
        
        except Exception as e:
            logger.exception("An error occurred while connecting to ArangoDB")
            return False
    
    def execute_query(
        self,
        query: str,
        bind_vars: Optional[Dict[str, Any]] = None,
        as_of_version: Optional[str] = None,
        as_of_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute an AQL query on the database.
        
        Args:
            query: The AQL query to execute
            bind_vars: Bind variables for the query (optional)
            as_of_version: Optional version to query against
            as_of_timestamp: Optional timestamp to query against
            
        Returns:
            Query execution result and metadata
        """
        logger.info(f"Executing AQL query: {query}")
        
        try:
            # Add version-aware clauses if specified
            if as_of_version or as_of_timestamp:
                version_clause = ""
                if as_of_version:
                    version_clause = f"FILTER doc.version <= @version"
                    bind_vars["version"] = as_of_version
                elif as_of_timestamp:
                    version_clause = f"FILTER doc.created_at <= @timestamp"
                    bind_vars["timestamp"] = as_of_timestamp
                
                # Insert the version clause into the query
                if "FOR" in query:
                    query_parts = query.split("FOR")
                    query = f"{query_parts[0]}FOR {version_clause} FOR{query_parts[1]}"
            
            cursor = self.db.aql.execute(query, bind_vars=bind_vars)
            results = [doc for doc in cursor]
            
            logger.info(f"Query executed successfully with {len(results)} results")
            return {
                "success": True,
                "result": results
            }
        
        except ArangoError as e:
            logger.error(f"AQL query execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
        except Exception as e:
            logger.exception("An error occurred while executing AQL query")
            return {
                "success": False,
                "error": str(e)
            }

def get_db_connection(db_name: str = "hades_db", host: str = "http://localhost:8529", username: str = "root", password: str = "") -> DBConnection:
    """
    Get a database connection instance.
    
    Args:
        db_name: The name of the database
        host: The host URL of the ArangoDB server
        username: The username for authentication
        password: The password for authentication
        
    Returns:
        A DBConnection instance
    """
    logger.info(f"Getting DBConnection for {db_name} at {host}")
    
    db_connection = DBConnection(db_name=db_name)
    if not db_connection.connect(host=host, username=username, password=password):
        raise Exception("Failed to connect to the database")
    
    return db_connection
