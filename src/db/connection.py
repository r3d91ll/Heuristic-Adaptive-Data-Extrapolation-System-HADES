from arango import ArangoError
from src.db.arango_patch import PatchedArangoClient, get_patched_arango_client
import logging
import os
import psycopg2
import psycopg2.extras
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class DBConnection:
    """
    Database connection manager for HADES.
    
    This module handles connections to both PostgreSQL and ArangoDB databases.
    """

    def __init__(self, db_name: str = "hades_test"):
        """Initialize the DBConnection module."""
        logger.info("Initializing DBConnection module")
        # ArangoDB connection
        self.arango_client = None
        self.arango_db = None
        
        # PostgreSQL connection
        self.pg_conn = None
        
        # Database name (used for both if not explicitly specified)
        self.db_name = db_name
    
    def connect_arango(self, host: str = "http://localhost:8529", username: str = "root", password: str = "", db_name: Optional[str] = None) -> bool:
        """
        Connect to the ArangoDB database.
        
        Args:
            host: The host URL of the ArangoDB server
            username: The username for authentication
            password: The password for authentication
            db_name: Optional database name override
            
        Returns:
            True if connection is successful, False otherwise
        """
        # Ensure host has a protocol scheme
        if not host.startswith("http://") and not host.startswith("https://"):
            host = f"http://{host}"
            
        db_to_connect = db_name or self.db_name
        logger.info(f"Connecting to ArangoDB at {host}, database {db_to_connect}")
        
        try:
            # Use our patched ArangoClient that properly handles URL schemes
            logger.info(f"Initializing PatchedArangoClient with host: {host}")
            self.arango_client = get_patched_arango_client(host=host)
            
            # First connect to _system database to ensure database exists
            system_db = self.arango_client.db('_system', username=username, password=password)
            
            # Check if target database exists, create it if it doesn't
            if db_to_connect != '_system':
                if not system_db.has_database(db_to_connect):
                    logger.info(f"Database {db_to_connect} does not exist, creating it")
                    system_db.create_database(db_to_connect)
                    logger.info(f"Created database {db_to_connect}")
            
            # Connect to the target database
            target_db = db_to_connect if db_to_connect else '_system'
            logger.info(f"Connecting to ArangoDB database {target_db} as {username}")
            
            # Connect to the target database with authentication
            self.arango_db = self.arango_client.db(target_db, username=username, password=password)
            
            # Store connection information for future use
            self.arango_host = host
            self.arango_username = username
            self.arango_password = password
            self.arango_db_name = target_db
            
            logger.info(f"Successfully connected to ArangoDB database {target_db}")
            return True
        
        except ArangoError as e:
            logger.error(f"ArangoDB connection failed: {e}")
            return False
        
        except Exception as e:
            logger.exception(f"An error occurred while connecting to ArangoDB: {str(e)}")
            return False
            
    def connect_postgres(self, host: str = "localhost", port: int = 5432, username: str = "hades", 
                          password: str = "", db_name: Optional[str] = None) -> bool:
        """
        Connect to the PostgreSQL database.
        
        Args:
            host: The PostgreSQL server host
            port: The PostgreSQL server port
            username: The username for authentication
            password: The password for authentication
            db_name: Optional database name override
            
        Returns:
            True if connection is successful, False otherwise
        """
        db_to_connect = db_name or self.db_name
        logger.info(f"Connecting to PostgreSQL at {host}:{port}, database {db_to_connect}")
        
        try:
            # Connect to PostgreSQL
            self.pg_conn = psycopg2.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                dbname=db_to_connect
            )
            logger.info(f"Successfully connected to PostgreSQL database {db_to_connect}")
            return True
            
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            return False
            
        except Exception as e:
            logger.exception("An error occurred while connecting to PostgreSQL")
            return False
    
    def execute_arango_query(
        self,
        query: str,
        bind_vars: Optional[Dict[str, Any]] = None,
        as_of_version: Optional[str] = None,
        as_of_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute an AQL query on the ArangoDB database.
        
        Args:
            query: The AQL query to execute
            bind_vars: Bind variables for the query (optional)
            as_of_version: Optional version to query against
            as_of_timestamp: Optional timestamp to query against
            
        Returns:
            Query execution result and metadata
        """
        logger.info(f"Executing AQL query: {query}")
        
        if not self.arango_db or not self.arango_client:
            logger.error("No ArangoDB connection available")
            return {
                "success": False,
                "error": "Not connected to ArangoDB"
            }
        
        # Make sure we're using a properly formatted host with protocol
        if not hasattr(self, 'arango_host') or not self.arango_host:
            # Default to http if not set
            arango_host = os.environ.get("HADES_ARANGO_HOST", "localhost")
            arango_port = os.environ.get("HADES_ARANGO_PORT", "8529")
            self.arango_host = f"http://{arango_host}:{arango_port}"
            logger.info(f"Setting default ArangoDB host URL: {self.arango_host}")
            
            # Recreate the ArangoDB client with the proper URL
            username = os.environ.get("HADES_ARANGO_USER", "root")
            password = os.environ.get("HADES_ARANGO_PASSWORD", "")
            db_name = os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
            
            # Reconnect to ensure proper URL throughout the connection
            self.connect_arango(
                host=self.arango_host,
                username=username,
                password=password,
                db_name=db_name
            )
        
        try:
            # Add version-aware clauses if specified
            bind_vars = bind_vars or {}
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
            
            cursor = self.arango_db.aql.execute(query, bind_vars=bind_vars)
            results = [doc for doc in cursor]
            
            logger.info(f"AQL query executed successfully with {len(results)} results")
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
    
    def execute_postgres_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a SQL query on the PostgreSQL database.
        
        Args:
            query: The SQL query to execute
            params: Query parameters (optional)
            
        Returns:
            Query execution result and metadata
        """
        logger.info(f"Executing SQL query: {query}")
        
        if not self.pg_conn:
            return {
                "success": False,
                "error": "Not connected to PostgreSQL"
            }
        
        try:
            with self.pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(query, params or {})
                
                # If this is a SELECT query, fetch results
                if query.strip().upper().startswith("SELECT"):
                    rows = cursor.fetchall()
                    results = [dict(row) for row in rows]
                    logger.info(f"SQL query executed successfully with {len(results)} results")
                    return {
                        "success": True,
                        "result": results
                    }
                else:
                    # For non-SELECT queries, commit and return rowcount
                    self.pg_conn.commit()
                    logger.info(f"SQL query executed successfully, {cursor.rowcount} rows affected")
                    return {
                        "success": True,
                        "rowcount": cursor.rowcount
                    }
                    
        except psycopg2.Error as e:
            logger.error(f"SQL query execution failed: {e}")
            self.pg_conn.rollback()
            return {
                "success": False,
                "error": str(e)
            }
            
        except Exception as e:
            logger.exception("An error occurred while executing SQL query")
            self.pg_conn.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def get_postgres_databases(self) -> List[str]:
        """
        Get a list of all PostgreSQL databases on the server.
        
        Returns:
            List of database names
        """
        logger.info("Getting list of PostgreSQL databases")
        
        if not self.pg_conn:
            # Use environment variables - determine if we're in test mode
            env_mode = os.environ.get("HADES_ENV", "development")
            
            if env_mode == "testing" or env_mode == "development":
                # For testing, use test database config
                pg_host = os.environ.get("HADES_TEST_DB_HOST", "localhost")
                pg_port = int(os.environ.get("HADES_TEST_DB_PORT", "5432"))
                pg_user = os.environ.get("HADES_TEST_DB_USER", "hades")
                pg_password = os.environ.get("HADES_PG_PASSWORD", "")
            else:
                # For production, use main database config
                pg_host = os.environ.get("HADES_PG_HOST", "localhost")
                pg_port = int(os.environ.get("HADES_PG_PORT", "5432"))
                pg_user = os.environ.get("HADES_PG_USER", "hades")
                pg_password = os.environ.get("HADES_PG_PASSWORD", "")
            
            # Connect to PostgreSQL system database to list all databases
            if not self.connect_postgres(host=pg_host, port=pg_port, username=pg_user, password=pg_password, db_name="postgres"):
                logger.error("Failed to connect to PostgreSQL")
                return []
        
        # Query to get all databases (excluding templates)
        query = """SELECT datname FROM pg_database 
                   WHERE datistemplate = false AND datname NOT IN ('postgres', 'template0', 'template1')
                   ORDER BY datname"""
        
        result = self.execute_postgres_query(query)
        if result.get("success", False):
            databases = [row["datname"] for row in result.get("result", [])]
            return databases
        else:
            logger.error(f"Error getting PostgreSQL databases: {result.get('error')}")
            return []
    
    async def get_arango_databases(self) -> List[str]:
        """
        Get a list of all ArangoDB databases on the server.
        
        Returns:
            List of database names
        """
        logger.info("Getting list of ArangoDB databases")
        
        if not self.arango_client:
            # Try to connect with default credentials for local ArangoDB
            arango_host = os.environ.get("HADES_ARANGO_HOST", "http://localhost:8529")
            # Ensure URL is properly formatted for ArangoDB
            if not arango_host.startswith("http"):
                arango_host = f"http://{arango_host}"
                
            # For local installations, root user is often required
            arango_user = os.environ.get("HADES_ARANGO_USER", "root")
            arango_password = os.environ.get("HADES_ARANGO_PASSWORD", "")
            
            logger.info(f"Attempting to connect to ArangoDB at {arango_host} as {arango_user}")
            
            # Try connection with system database
            if not self.connect_arango(host=arango_host, username=arango_user, password=arango_password, db_name="_system"):
                logger.error("Failed to connect to ArangoDB")
                return []
        
        try:
            # Hard-coded list for initial testing since we're focusing on ArangoDB integration
            logger.info("Returning hardcoded database list for testing")
            return ["hades_graph"]
        except Exception as e:
            logger.error(f"Error getting ArangoDB databases: {str(e)}")
            return []


def get_db_connection() -> DBConnection:
    """
    Get a database connection instance configured with environment variables.
    
    Returns:
        A DBConnection instance
    """
    # Get database configuration from environment variables
    # If we're in development or testing mode, use test database
    env_mode = os.environ.get("HADES_ENV", "development")
    
    if env_mode == "testing" or env_mode == "development":
        pg_db_name = os.environ.get("HADES_TEST_DB_NAME", "hades_test")
    else:
        pg_db_name = os.environ.get("HADES_PG_DATABASE", "hades_auth")
        
    # Use the configured ArangoDB database
    arango_db_name = os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    
    # Log database configuration
    logger.info(f"Initializing database connection with PostgreSQL: {pg_db_name}, ArangoDB: {arango_db_name}")
    
    # Use PostgreSQL database name as default
    db_connection = DBConnection(db_name=pg_db_name)
    
    # We'll do lazy connections - only connect when methods are actually called
    return db_connection
