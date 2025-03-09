"""
Pytest configuration for HADES tests.

This module provides fixtures and configuration for all tests.
"""
import os
import sys
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
pytest.importorskip("pytest_asyncio")
from fastapi.testclient import TestClient

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


@pytest.fixture
def mock_db_connection(monkeypatch):
    """
    Mock the database connection for testing.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        Mock database connection object
    """
    class MockDatabaseConnection:
        def __init__(self):
            self.queries = []
            self.results = {}
            self.connection_active = True
            self._client = self  # Initialize with self as the default client
        
        def execute_query(self, query, bind_vars=None):
            self.queries.append((query, bind_vars))
            return self.results.get((query, str(bind_vars)), {"result": [], "success": True})
        
        def close(self):
            self.connection_active = False
        
        def set_result(self, query, bind_vars, result):
            self.results[(query, str(bind_vars))] = result
        
        def initialize_database(self):
            # Mock the database initialization
            pass
            
        @property
        def client(self):
            return self._client
            
        @client.setter
        def client(self, value):
            self._client = value
            
        def get_db(self):
            # Simulate the context manager
            class DBContextManager:
                def __enter__(self_cm):
                    return MagicMock()
                    
                def __exit__(self_cm, exc_type, exc_val, exc_tb):
                    pass
            return DBContextManager()
    
    mock_conn = MockDatabaseConnection()
    
    # Use monkeypatch to replace the actual connection with our mock
    from src.db import connection
    monkeypatch.setattr(connection, "connection", mock_conn)
    
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
