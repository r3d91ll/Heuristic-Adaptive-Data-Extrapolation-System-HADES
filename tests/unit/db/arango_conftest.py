"""
ArangoDB-specific pytest fixtures for database tests.
This file contains fixtures that use real ArangoDB connections instead of mocks.
"""
import os
import pytest
from arango import ArangoClient, ArangoError

# Import the DBConnection class
from src.db.connection import DBConnection, get_db_connection

# Try to import test environment variables from setup script
try:
    from tests.arango_test_env import ARANGO_TEST_PARAMS as DEFAULT_ARANGO_PARAMS
except ImportError:
    # Default connection parameters if setup script hasn't been run
    DEFAULT_ARANGO_PARAMS = {
        "host": "http://localhost:8529",
        "username": "hades",
        "password": "",  # Will be read from .env
        "database": "hades_graph"
    }

def get_arango_params():
    """Get ArangoDB connection parameters from environment or defaults."""
    # First check environment variables
    params = {
        "host": os.environ.get("HADES_ARANGO_HOST", DEFAULT_ARANGO_PARAMS["host"]),
        "username": os.environ.get("HADES_ARANGO_USER", DEFAULT_ARANGO_PARAMS["username"]),
        "password": os.environ.get("HADES_ARANGO_PASSWORD", DEFAULT_ARANGO_PARAMS["password"]),
        "database": os.environ.get("HADES_ARANGO_DATABASE", DEFAULT_ARANGO_PARAMS["database"])
    }
    
    # If password is empty, try to read from .env file
    if not params["password"]:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        try:
                            key, value = line.strip().split('=', 1)
                            if key == 'HADES_ARANGO_PASSWORD':
                                params['password'] = value
                        except ValueError:
                            pass
    
    return params

@pytest.fixture(scope="session")
def arango_connection_params():
    """Return ArangoDB connection parameters."""
    return get_arango_params()

@pytest.fixture(scope="session")
def arango_client(arango_connection_params):
    """Create a real ArangoDB client for testing."""
    try:
        client = ArangoClient(hosts=arango_connection_params["host"])
        # Test connection
        db = client.db(
            arango_connection_params["database"],
            username=arango_connection_params["username"],
            password=arango_connection_params["password"],
            verify=True
        )
        # Check if connected
        db.properties()
        yield client
    except ArangoError as e:
        pytest.skip(f"Could not connect to ArangoDB: {e}")

@pytest.fixture(scope="session")
def arango_db(arango_client, arango_connection_params):
    """Create a real ArangoDB database connection for testing."""
    try:
        db = arango_client.db(
            arango_connection_params["database"],
            username=arango_connection_params["username"],
            password=arango_connection_params["password"],
            verify=True
        )
        yield db
    except ArangoError as e:
        pytest.skip(f"Could not connect to ArangoDB database: {e}")

@pytest.fixture
def real_db_connection(arango_connection_params):
    """Create a real DBConnection instance with test database connection."""
    # Create a new DBConnection instance
    db_conn = DBConnection(db_name=arango_connection_params["database"])
    
    # Connect to the database
    connected = db_conn.connect(
        host=arango_connection_params["host"],
        username=arango_connection_params["username"],
        password=arango_connection_params["password"]
    )
    
    if not connected:
        pytest.skip("Could not connect to ArangoDB")
    
    yield db_conn
    
    # No need to clean up as we'll keep the test collections for reuse

@pytest.fixture
def clean_test_collections(arango_db):
    """Clean up test collections before and after tests."""
    # List of test collections to clean
    test_collections = ["test_entities", "test_contexts", "test_domains", "test_relationships"]
    
    # Clean collections before tests
    for collection_name in test_collections:
        if arango_db.has_collection(collection_name):
            collection = arango_db.collection(collection_name)
            collection.truncate()
    
    yield
    
    # Clean collections after tests
    for collection_name in test_collections:
        if arango_db.has_collection(collection_name):
            collection = arango_db.collection(collection_name)
            collection.truncate()
