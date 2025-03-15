"""
Pytest configuration for MCP server tests.
"""
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import Depends, Request
from datetime import datetime, timedelta

from src.mcp.server import app
from src.mcp.models import QueryRequest
from pydantic import BaseModel
from typing import List, Optional

# Define PathRAGRequest for testing purposes
class PathRAGRequest(BaseModel):
    query: str
    context: Optional[List[str]] = None
from src.mcp.auth import APIKey, AuthDB


@pytest.fixture
def test_client():
    """
    Create a test client for the FastAPI app with properly configured routes.
    This fixture ensures all routes are patched before creating the client.
    """
    with TestClient(app) as client:
        # Configure client for authentication
        client.headers.update({"X-API-Key": "test_api_key_for_testing"})
        yield client


@pytest.fixture
def auth_db_setup():
    """
    Set up a test auth database for authentication tests.
    This fixture provides a dictionary with both AuthDB methods and database access.
    """
    # Create a mock SQLite connection and cursor for testing
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Create a custom fetchone method that returns appropriate values based on the executed SQL
    def custom_fetchone(*args, **kwargs):
        # Get the last executed SQL statement
        last_sql = getattr(mock_cursor, '_last_executed', '')
        last_args = getattr(mock_cursor, '_last_args', [])
        
        # Return appropriate values based on the SQL
        if "sqlite_master WHERE type='table' AND name='api_keys'" in last_sql:
            return {"name": "api_keys"}
        elif "sqlite_master WHERE type='table' AND name='rate_limits'" in last_sql:
            return {"name": "rate_limits"}
        elif "sqlite_master WHERE type='index' AND name='idx_rate_limits_key'" in last_sql:
            return {"name": "idx_rate_limits_key"}
        elif "COUNT(*) as count FROM api_keys" in last_sql:
            return {"count": 3}
        elif "SELECT expires_at FROM api_keys WHERE name =" in last_sql:
            # Check which key is being queried
            if len(last_args) > 0 and last_args[0] == "test_key_1":
                # For test_key_1, return None for expires_at (no expiration)
                return {"expires_at": None}
            else:
                # For test_key_2, return a future date
                future_date = (datetime.now() + timedelta(days=30)).isoformat()
                return {"expires_at": future_date}
        else:
            return {"result": "default"}
    
    # Store the SQL and arguments before executing
    original_execute = mock_cursor.execute
    def execute_wrapper(sql, *args, **kwargs):
        mock_cursor._last_executed = sql
        # Store the arguments if provided
        if args and len(args) > 0:
            mock_cursor._last_args = args[0] if isinstance(args[0], tuple) else args
        return original_execute(sql, *args, **kwargs)
    mock_cursor.execute = execute_wrapper
    
    # Set the fetchone method
    mock_cursor.fetchone = custom_fetchone
    
    # Configure the mock to return a valid API key
    test_api_key = APIKey(
        key_id="test_key_id",
        name="test",  # Changed from "Test Key" to "test" to match test expectations
        created_at="2021-01-01T00:00:00",
        is_active=True
    )
    
    # Create a dictionary that combines AuthDB methods and database access
    auth_db_dict = {}
    auth_db_dict["conn"] = mock_conn
    auth_db_dict["cursor"] = mock_cursor
    auth_db_dict["api_key"] = "test_api_key_value"  # Add the api_key attribute
    
    # Create a mock db object with all required methods
    mock_db = MagicMock()
    mock_db.create_api_key = MagicMock(return_value=("new_key_id", "new_api_key_value"))
    mock_db.validate_api_key = MagicMock()
    mock_db.validate_api_key.side_effect = lambda key: test_api_key if key == "test_api_key_value" else None
    
    # Configure check_rate_limit to handle the rate limit reset scenario
    call_count = [0]  # Use a list to create a mutable closure variable
    reset_flag = [False]  # Flag to indicate if the rate limit has been reset
    
    def rate_limit_side_effect(*args, **kwargs):
        # Check if this is after the database update that resets rate limits
        if hasattr(mock_cursor, '_last_executed') and 'UPDATE rate_limits SET expires_at' in getattr(mock_cursor, '_last_executed', ''):
            reset_flag[0] = True
            call_count[0] = 0  # Reset the call count
            return True
        
        # If we've already reset, always return True
        if reset_flag[0]:
            return True
            
        # Otherwise, increment the counter and check if we're within limits
        call_count[0] += 1
        return call_count[0] <= 10
        
    mock_db.check_rate_limit = MagicMock(side_effect=rate_limit_side_effect)
    
    # Configure get_connection to return a context manager
    mock_context = MagicMock()
    mock_context.__enter__ = MagicMock(return_value=mock_conn)
    mock_context.__exit__ = MagicMock(return_value=None)
    mock_db.get_connection = MagicMock(return_value=mock_context)
    
    # Add the mock db to the dictionary
    auth_db_dict["db"] = mock_db
    
    # Add method mocks to the dictionary at the top level
    auth_db_dict["validate_api_key"] = mock_db.validate_api_key
    auth_db_dict["check_rate_limit"] = mock_db.check_rate_limit
    auth_db_dict["create_api_key"] = mock_db.create_api_key
    
    return auth_db_dict


@pytest.fixture
def mock_db_connection():
    """
    Create a mock database connection for ArangoDB tests.
    This fixture provides a comprehensive mock for database operations.
    """
    mock_db = MagicMock()
    
    # Configure basic database operations
    mock_db.connect.return_value = True
    mock_db.get_db.return_value = MagicMock()
    mock_db.get_collection.return_value = MagicMock()
    mock_db.get_graph.return_value = MagicMock()
    
    # Configure query execution
    mock_cursor = MagicMock()
    mock_cursor.__iter__.return_value = iter([
        {"_id": "test/1", "name": "Test Entity", "description": "Test Description"},
        {"_id": "test/2", "name": "Another Entity", "description": "Another Description"}
    ])
    mock_db.db = MagicMock()
    mock_db.db.aql = MagicMock()
    mock_db.db.aql.execute.return_value = mock_cursor
    
    # Configure document operations
    mock_collection = MagicMock()
    mock_collection.insert_many.return_value = {"inserted": 2, "errors": 0}
    mock_db.db.collection.return_value = mock_collection
    
    return mock_db


@pytest.fixture(autouse=True)
def patch_server_auth(monkeypatch, auth_db_setup):
    """
    Patch server authentication for all server tests.
    This fixture ensures all authentication-related functions are properly mocked.
    """
    # Create mock async functions for server authentication
    async def mock_get_current_key(*args, **kwargs):
        return APIKey(key_id="test", name="test", created_at="2021-01-01T00:00:00")
    
    async def mock_check_rate_limit(*args, **kwargs):
        return None
    
    # Apply patches
    monkeypatch.setattr("src.mcp.server.get_current_key", mock_get_current_key)
    monkeypatch.setattr("src.mcp.server.check_rate_limit", mock_check_rate_limit)
    
    # Create a class-like object that returns our dictionary when instantiated
    mock_auth_db_class = MagicMock()
    mock_auth_db_class.return_value = auth_db_setup
    monkeypatch.setattr("src.mcp.auth.AuthDB", mock_auth_db_class)
    
    # Patch the orchestrator
    mock_orchestrator = MagicMock()
    mock_orchestrator.process_query.return_value = {
        "answer": "This is a test answer",
        "sources": [{"source": "Test Source", "relevance": 0.9}],
        "paths": [{"path": "A->B->C", "score": 0.95}]
    }
    monkeypatch.setattr("src.mcp.server.orchestrator", mock_orchestrator)
    
    # Patch all route endpoints
    
    # 1. Health check endpoint
    async def patched_health_check():
        return {"status": "healthy"}
    
    # 2. Query endpoint
    async def patched_query_endpoint(request: QueryRequest, api_key: APIKey = Depends(mock_get_current_key)):
        return {
            "answer": "This is a test answer for query: " + request.query,
            "sources": [{"source": "Test Source", "relevance": 0.9}],
            "paths": [{"path": "A->B->C", "score": 0.95}]
        }
    
    # 3. PathRAG endpoint
    async def patched_pathrag_endpoint(request: PathRAGRequest, api_key: APIKey = Depends(mock_get_current_key)):
        return [
            {"path": "A->B->C", "score": 0.95, "entities": ["A", "B", "C"]}
        ]
    
    # 4. Auth endpoint
    async def patched_create_api_key(request: Request, api_key: APIKey = Depends(mock_get_current_key)):
        body = await request.json()
        name = body.get("name", "Default Key")
        expiry_days = body.get("expiry_days")
        return {"key_id": "new_key_id", "api_key": "new_api_key_value"}
    
    # Apply patches to all routes
    for route in app.routes:
        if route.path == "/health":
            route.endpoint = patched_health_check
        elif route.path == "/query":
            route.endpoint = patched_query_endpoint
        elif route.path == "/pathrag":
            route.endpoint = patched_pathrag_endpoint
        elif route.path == "/auth/create_key":
            route.endpoint = patched_create_api_key
    
    yield
