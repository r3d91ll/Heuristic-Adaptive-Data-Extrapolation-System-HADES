"""
Pytest configuration for HADES tests.

This module provides fixtures and configuration for all tests.
"""
# Import test configuration first to set environment variables
import tests.test_config

import os
import sys
import sqlite3
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

import pytest
pytest.importorskip("pytest_asyncio")
from fastapi.testclient import TestClient

# Import our test patches
from tests.patch_auth import setup_test_environment, patch_server_module, patch_data_ingestion

# Import real database fixtures
try:
    # Import fixtures from the consolidated test setup
    from tests.unit.db.arango_conftest import *
    from tests.unit.mcp.pg_conftest import *
    
    # Ensure test databases are set up
    from tests.setup_test_databases import TestDatabaseSetup
    # Initialize but don't force recreation during test runs
    TestDatabaseSetup(force=False)
except ImportError as e:
    print(f"Warning: Could not import database fixtures: {e}")

# Apply patches at the module level
setup_test_environment()

@pytest.fixture(scope="session", autouse=True)
def apply_test_patches():
    """Apply all test patches at the start of the test session."""
    patch_server_module()
    patch_data_ingestion()
    yield

# Add the src directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import fixtures after path adjustment
from src.mcp.server import app
from src.utils.config import config, load_config


@pytest.fixture
def test_client():
    """
    Create a FastAPI TestClient for the MCP server.
    
    Returns:
        TestClient: A test client for the MCP server
    """
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_core_components(monkeypatch):
    """
    Mock core components to avoid database connection issues.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Mock the TripleContextRestoration class
    try:
        from src.tcr.restoration import TripleContextRestoration
        
        def mock_tcr_init(self, *args, **kwargs):
            self.initialized = True
            self.nlp = MagicMock()
            self.db_connection = MagicMock()
            # Add mock methods that might be called during tests
            self.extract_triples = MagicMock(return_value=[])
            self.restore_context = MagicMock(return_value={})
        
        monkeypatch.setattr(TripleContextRestoration, "__init__", mock_tcr_init)
    except ImportError:
        pass
    
    # Mock the GraphCheck class
    try:
        from src.graphcheck.verification import GraphCheck
        
        def mock_graphcheck_init(self, *args, **kwargs):
            self.initialized = True
            self.model = MagicMock()
            self.tokenizer = MagicMock()
            # Add mock methods that might be called during tests
            self.verify_graph = MagicMock(return_value={"score": 0.95, "valid": True})
        
        monkeypatch.setattr(GraphCheck, "__init__", mock_graphcheck_init)
    except ImportError:
        pass
    
    # We're using real PostgreSQL connections as per user preference
    # No mocking needed here

@pytest.fixture
def mock_db_connection(monkeypatch):
    """
    Mock the database connection for testing.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        Mock database connection object
    """
    import logging
    
    class MockDatabaseConnection:
        def __init__(self):
            self.queries = []
            self.results = {}
            self.connection_active = True
            self._client = MagicMock()  # Mock ArangoClient
            self.db_name = "hades_test"
            
            # Create a properly structured mock database
            self.db = MagicMock()
            self.db.aql = MagicMock()
            self.db.aql.execute = MagicMock(return_value=[])
            
            # Set up collections
            self.collections = {}
            for collection_name in ["nodes", "edges", "paths", "triples"]:
                mock_collection = MagicMock()
                mock_collection.name = collection_name
                mock_collection.insert = MagicMock(return_value={"_id": f"{collection_name}/test_id"})
                mock_collection.get = MagicMock(return_value={"_id": f"{collection_name}/test_id", "data": "test_data"})
                mock_collection.update = MagicMock(return_value=True)
                mock_collection.delete = MagicMock(return_value=True)
                self.collections[collection_name] = mock_collection
            
            # Set up graphs
            self.graphs = {}
            mock_graph = MagicMock()
            mock_graph.name = "knowledge_graph"
            self.graphs["knowledge_graph"] = mock_graph
            
            # Configure client to return our db
            self._client.db.return_value = self.db
        
        def connect(self, host="http://localhost:8529", username="root", password=""):
            """Mock the connect method to always return success"""
            logger = logging.getLogger("test")
            logger.info(f"Mock connecting to ArangoDB at {host}")
            return True
            
        def execute_query(self, query, bind_vars=None):
            self.queries.append((query, bind_vars))
            return self.results.get((query, str(bind_vars)), {"result": [], "success": True})
        
        def close(self):
            self.connection_active = False
        
        def set_result(self, query, bind_vars, result):
            self.results[(query, str(bind_vars))] = result
        
        def initialize_database(self):
            # Mock the database initialization
            return True
            
        @property
        def client(self):
            return self._client
            
        @client.setter
        def client(self, value):
            self._client = value
        
        def get_collection(self, collection_name):
            """Get a mock collection"""
            if collection_name not in self.collections:
                self.collections[collection_name] = MagicMock()
                self.collections[collection_name].name = collection_name
            return self.collections[collection_name]
        
        def get_graph(self, graph_name):
            """Get a mock graph"""
            if graph_name not in self.graphs:
                self.graphs[graph_name] = MagicMock()
                self.graphs[graph_name].name = graph_name
            return self.graphs[graph_name]
            
        def get_db(self):
            # Return our mock db directly
            return self.db
            
        def get_database(self):
            # Return our mock db directly
            return self.db
    
    mock_conn = MockDatabaseConnection()
    
    # Use monkeypatch to replace the actual connection with our mock
    from src.db import connection
    monkeypatch.setattr(connection, "connection", mock_conn)
    
    # Also patch any direct imports of ArangoClient
    from arango import ArangoClient
    mock_arango_client = MagicMock()
    mock_db = MagicMock()
    mock_arango_client.db.return_value = mock_db
    monkeypatch.setattr("arango.ArangoClient", lambda *args, **kwargs: mock_arango_client)
    
    # Patch the PathRAG class to avoid database connection
    try:
        from src.rag.path_rag import PathRAG
        
        def mock_init(self, *args, **kwargs):
            self.db_connection = mock_conn
            self.db = MagicMock()
            self.collection = MagicMock()
            self.graph = MagicMock()
            self.initialized = True
            # Add mock methods that might be called during tests
            self.retrieve_paths = MagicMock(return_value={"paths": []})
            self.generate_response = MagicMock(return_value="This is a mock response")
        
        monkeypatch.setattr(PathRAG, "__init__", mock_init)
    except ImportError:
        pass
    
    return mock_conn


@pytest.fixture
def test_config(monkeypatch):
    """
    Configure test settings.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        Config object with test settings
    """
    # Create a test config with specific values for testing
    test_config_dict = {
        "env": "test",
        "debug": True,
        "log_level": "INFO",
        "db": {
            "host": "http://localhost:8529",
            "username": "root",
            "password": "password",
            "database": "hades_test"
        },
        "mcp": {
            "host": "0.0.0.0",
            "port": 8000,
            "auth_enabled": False,
            "auth": {
                "db_path": ":memory:",
                "enabled": False,
                "token_expiry_days": 30,
                "rate_limit_rpm": 60,
                "admin_keys": ["admin1", "admin2", "admin3"]
            }
        }
    }
    
    # Set up environment variables based on test config
    with patch.dict(os.environ, {}, clear=True):
        # Mock all environment variable parsing
        with patch("src.utils.config.load_config") as mock_load_config:
            mock_load_config.return_value = config
            
            # Set test configuration
            monkeypatch.setattr(config, "env", "test")
            monkeypatch.setattr(config.mcp, "auth_enabled", False)
            monkeypatch.setattr(config.mcp.auth, "admin_keys", ["admin1", "admin2", "admin3"])
            monkeypatch.setattr(config.mcp.auth, "db_path", ":memory:")
            
            # Set database configuration
            if hasattr(config, "db"):
                monkeypatch.setattr(config.db, "host", "http://localhost:8529")
                monkeypatch.setattr(config.db, "username", "root")
                monkeypatch.setattr(config.db, "password", "password")
                monkeypatch.setattr(config.db, "database", "hades_test")
            
            # Use in-memory SQLite for auth testing
            from src.mcp.auth import auth_db
            monkeypatch.setattr(auth_db, "db_path", ":memory:")
            
            return config


@pytest.fixture
def auth_db_setup():
    """
    Set up an in-memory auth database for testing.
    
    Returns:
        Auth database instance
    """
    from src.mcp.auth import AuthDB
    
    # Use in-memory SQLite for testing
    test_auth_db = AuthDB()
    test_auth_db.db_path = ":memory:"
    
    # Create the database schema
    conn = sqlite3.connect(":memory:")
    # Set row_factory to enable dictionary access
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create API keys table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        key_id TEXT PRIMARY KEY,
        key_hash TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT,
        is_active BOOLEAN DEFAULT TRUE
    )
    """)
    
    # Create rate limits table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rate_limits (
        key TEXT NOT NULL,
        requests INTEGER DEFAULT 1,
        window_start TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )
    """)
    
    # Add indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_key ON rate_limits(key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rate_limits_expires ON rate_limits(expires_at)")
    
    conn.commit()
    
    # Create a test API key
    import hashlib
    import uuid
    from datetime import datetime
    
    key_id = str(uuid.uuid4())
    api_key = str(uuid.uuid4())
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    created_at = datetime.now().isoformat()
    
    cursor.execute(
        "INSERT INTO api_keys (key_id, key_hash, name, created_at, is_active) VALUES (?, ?, ?, ?, ?)",
        (key_id, key_hash, "test", created_at, True)
    )
    conn.commit()
    
    # Override the get_connection method
    def get_test_connection():
        # Ensure row_factory is set for every connection
        conn.row_factory = sqlite3.Row
        return conn
    
    test_auth_db.get_connection = get_test_connection
    
    return {
        "db": test_auth_db,
        "key_id": key_id,
        "api_key": api_key,
        "conn": conn
    }


@pytest.fixture
def mock_llm_response(monkeypatch):
    """
    Mock LLM responses for tests that use language models.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        Function to set mock responses
    """
    class MockLLM:
        def __init__(self):
            self.responses = {}
        
        def set_response(self, query, response):
            self.responses[query] = response
        
        def generate(self, query, **kwargs):
            return self.responses.get(query, "Mock response for: " + query)
    
    mock_llm = MockLLM()
    
    # Use monkeypatch to replace LLM-related functions
    try:
        from src.core import orchestrator
        monkeypatch.setattr(orchestrator, "process_query", 
                          lambda query, **kwargs: {
                              "answer": mock_llm.generate(query),
                              "sources": [{"source": "Test Source", "relevance": 0.9}],
                              "paths": [{"path": "A->B->C", "score": 0.95}]
                          })
    except (ImportError, AttributeError):
        pass
    
    return mock_llm
