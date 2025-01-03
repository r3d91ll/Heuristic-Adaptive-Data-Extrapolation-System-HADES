"""Tests for the database service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
from arango import ArangoClient

from hades.core.config import DatabaseConfig
from hades.core.exceptions import MCPError
from hades.services.database import DatabaseService

@pytest.fixture
def database_config():
    """Create a database configuration for testing."""
    return DatabaseConfig(
        host="test-host",
        port=8529,
        username="test-user",
        password="test-pass",
        database="test-db"
    )

@pytest.fixture
def database_service(database_config):
    """Create a database service instance for testing."""
    return DatabaseService(database_config)

def test_database_service_initialization(database_config):
    """Test database service initialization."""
    service = DatabaseService(database_config)
    assert service.config["host"] == "test-host"
    assert service.config["port"] == 8529
    assert service.config["username"] == "test-user"
    assert service.config["password"] == "test-pass"
    assert service.config["database"] == "test-db"
    assert not service._initialized
    assert service._client is None
    assert service._db is None

@pytest.mark.asyncio
async def test_create_client(database_service):
    """Test client creation."""
    with patch('hades.services.database.ArangoClient') as mock_client:
        # Mock the client's db() method
        mock_db = MagicMock()
        mock_client.return_value.db.return_value = mock_db
        
        # Mock successful version check
        mock_db.version.return_value = "3.7.0"
        
        client = database_service._create_client()
        assert client is not None
        mock_client.assert_called_once()

@pytest.mark.asyncio
async def test_database_service_initialize_success(database_service):
    """Test successful database service initialization."""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_client.db.return_value = mock_db
    
    with patch.object(database_service, '_create_client', return_value=mock_client):
        await database_service.initialize()
    
    assert database_service._initialized
    assert database_service._client is mock_client
    assert database_service._db is mock_db
    mock_client.db.assert_called_once_with(
        database_service.config["database"],
        username=database_service.config["username"],
        password=database_service.config["password"]
    )

@pytest.mark.asyncio
async def test_database_service_initialize_failure(database_service):
    """Test database service initialization failure."""
    mock_client = MagicMock()
    mock_client.db.side_effect = Exception("DB connection failed")
    
    with patch.object(database_service, '_create_client', return_value=mock_client), \
         pytest.raises(MCPError) as exc_info:
        await database_service.initialize()
    
    assert not database_service._initialized
    assert exc_info.value.code == "INIT_ERROR"
    assert "DB connection failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_database_service_shutdown_success(database_service):
    """Test successful database service shutdown."""
    database_service._client = MagicMock()
    database_service._db = MagicMock()
    database_service._initialized = True
    
    await database_service.shutdown()
    
    assert not database_service._initialized
    assert database_service._client is None
    assert database_service._db is None

@pytest.mark.asyncio
async def test_database_service_shutdown_handles_errors(database_service):
    """Test database service shutdown with errors."""
    mock_client = MagicMock()
    mock_client.close.side_effect = Exception("Shutdown failed")
    database_service._client = mock_client
    database_service._initialized = True
    
    # Should not raise exception
    await database_service.shutdown()
    
    assert not database_service._initialized
    assert database_service._client is None

@pytest.mark.asyncio
async def test_execute_query_success(database_service):
    """Test successful query execution."""
    mock_cursor = [{"_id": "1", "name": "test"}]
    database_service._initialized = True
    database_service._db = MagicMock()
    database_service._db.aql = MagicMock()
    database_service._db.aql.execute = MagicMock(return_value=mock_cursor)
    
    result = await database_service.execute_query("FOR doc IN collection RETURN doc")
    assert result == mock_cursor

@pytest.mark.asyncio
async def test_execute_query_not_initialized(database_service):
    """Test query execution when service is not initialized."""
    with pytest.raises(MCPError) as exc_info:
        await database_service.execute_query("FOR doc IN collection RETURN doc")
    assert "Service must be initialized before use" in str(exc_info.value)

@pytest.mark.asyncio
async def test_execute_query_failure(database_service):
    """Test query execution failure."""
    database_service._initialized = True
    database_service._db = MagicMock()
    database_service._db.aql = MagicMock()
    database_service._db.aql.execute = MagicMock(side_effect=Exception("Query failed"))
    
    with pytest.raises(MCPError) as exc_info:
        await database_service.execute_query("FOR doc IN collection RETURN doc")
    assert "Query failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_health_check_success(database_service):
    """Test successful health check."""
    database_service._initialized = True
    database_service._db = MagicMock()
    database_service._db.version = MagicMock(return_value="3.9.1")
    
    health = await database_service.health_check()
    assert health["status"] == "ok"
    assert health["version"] == "3.9.1"

@pytest.mark.asyncio
async def test_health_check_not_initialized(database_service):
    """Test health check when service is not initialized."""
    health = await database_service.health_check()
    assert health["status"] == "not_initialized"

@pytest.mark.asyncio
async def test_health_check_failure(database_service):
    """Test health check failure."""
    database_service._initialized = True
    database_service._db = MagicMock()
    database_service._db.version = MagicMock(side_effect=Exception("Version check failed"))
    
    health = await database_service.health_check()
    assert health["status"] == "error"
    assert "Version check failed" in health["message"] 

@pytest.mark.asyncio
async def test_create_client_error(database_service):
    """Test client creation error."""
    with patch('hades.services.database.ArangoClient', side_effect=Exception("Connection error")):
        with pytest.raises(MCPError) as exc_info:
            database_service._create_client()
        assert exc_info.value.code == "INIT_ERROR"
        assert "Connection error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_initialize_client_creation_error(database_service):
    """Test initialization with client creation error."""
    with patch.object(database_service, '_create_client', side_effect=MCPError("INIT_ERROR", "Client creation failed")):
        with pytest.raises(MCPError) as exc_info:
            await database_service.initialize()
        assert exc_info.value.code == "INIT_ERROR"
        assert "Client creation failed" in str(exc_info.value)
        assert not database_service._initialized

@pytest.mark.asyncio
async def test_execute_query_with_bind_vars(database_service):
    """Test query execution with bind variables."""
    mock_cursor = [{"_id": "1", "name": "test"}]
    database_service._initialized = True
    database_service._db = MagicMock()
    database_service._db.aql = MagicMock()
    database_service._db.aql.execute = MagicMock(return_value=mock_cursor)
    
    bind_vars = {"name": "test"}
    result = await database_service.execute_query(
        "FOR doc IN collection FILTER doc.name == @name RETURN doc",
        bind_vars=bind_vars
    )
    
    assert result == mock_cursor
    database_service._db.aql.execute.assert_called_once_with(
        "FOR doc IN collection FILTER doc.name == @name RETURN doc",
        bind_vars=bind_vars
    )

@pytest.mark.asyncio
async def test_execute_query_with_empty_bind_vars(database_service):
    """Test query execution with empty bind variables."""
    mock_cursor = [{"_id": "1", "name": "test"}]
    database_service._initialized = True
    database_service._db = MagicMock()
    database_service._db.aql = MagicMock()
    database_service._db.aql.execute = MagicMock(return_value=mock_cursor)
    
    result = await database_service.execute_query(
        "FOR doc IN collection RETURN doc",
        bind_vars={}
    )
    
    assert result == mock_cursor
    database_service._db.aql.execute.assert_called_once_with(
        "FOR doc IN collection RETURN doc",
        bind_vars={}
    )

@pytest.mark.asyncio
async def test_execute_query_with_none_bind_vars(database_service):
    """Test query execution with None bind variables."""
    mock_cursor = [{"_id": "1", "name": "test"}]
    database_service._initialized = True
    database_service._db = MagicMock()
    database_service._db.aql = MagicMock()
    database_service._db.aql.execute = MagicMock(return_value=mock_cursor)
    
    result = await database_service.execute_query(
        "FOR doc IN collection RETURN doc",
        bind_vars=None
    )
    
    assert result == mock_cursor
    database_service._db.aql.execute.assert_called_once_with(
        "FOR doc IN collection RETURN doc",
        bind_vars={}
    )

@pytest.mark.asyncio
async def test_execute_query_invalid_query(database_service):
    """Test query execution with invalid query."""
    database_service._initialized = True
    database_service._db = MagicMock()
    database_service._db.aql = MagicMock()
    database_service._db.aql.execute = MagicMock(side_effect=Exception("Invalid query syntax"))
    
    with pytest.raises(MCPError) as exc_info:
        await database_service.execute_query("INVALID QUERY")
    assert exc_info.value.code == "QUERY_ERROR"
    assert "Invalid query syntax" in str(exc_info.value)
    assert "INVALID QUERY" in str(exc_info.value.details["query"])

@pytest.mark.asyncio
async def test_execute_query_invalid_bind_vars(database_service):
    """Test query execution with invalid bind variables."""
    database_service._initialized = True
    database_service._db = MagicMock()
    database_service._db.aql = MagicMock()
    database_service._db.aql.execute = MagicMock(side_effect=Exception("Invalid bind variable"))
    
    bind_vars = {"invalid": object()}  # Invalid bind variable type
    with pytest.raises(MCPError) as exc_info:
        await database_service.execute_query(
            "FOR doc IN collection FILTER doc.name == @invalid RETURN doc",
            bind_vars=bind_vars
        )
    assert exc_info.value.code == "QUERY_ERROR"
    assert "Invalid bind variable" in str(exc_info.value)
    assert bind_vars == exc_info.value.details["bind_vars"] 

@pytest.mark.asyncio
async def test_double_initialization(database_service, mocker):
    """Test that initializing an already initialized service is a no-op."""
    # Mock the create client method to avoid actual DB connection
    mocker.patch.object(
        database_service,
        '_create_client',
        return_value=mocker.Mock()
    )
    
    await database_service.initialize()
    assert database_service._initialized
    
    # Second initialization should be a no-op
    await database_service.initialize()
    assert database_service._initialized
    
    # Verify _create_client was called only once
    database_service._create_client.assert_called_once() 