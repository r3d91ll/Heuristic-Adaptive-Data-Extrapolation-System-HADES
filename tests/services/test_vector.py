"""Tests for vector service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pymilvus import Collection, connections
from pymilvus.exceptions import ConnectionNotExistException

from hades.core.config import MilvusConfig
from hades.core.exceptions import MCPError
from hades.services.vector import VectorService

@pytest.fixture
def milvus_config():
    """Create test Milvus configuration."""
    return MilvusConfig(
        host="test-host",
        port=19530,
        user="test-user",
        password="test-pass",
        collection="test-collection"
    )

@pytest.fixture
def vector_service(milvus_config):
    """Create vector service instance."""
    return VectorService(milvus_config)

@pytest.mark.asyncio
async def test_vector_service_initialization(vector_service):
    """Test vector service initialization."""
    assert vector_service.config["host"] == "test-host"
    assert vector_service.config["port"] == 19530
    assert vector_service.config["collection"] == "test-collection"
    assert not vector_service._initialized

@pytest.mark.asyncio
async def test_vector_service_initialize_success(vector_service):
    """Test successful vector service initialization."""
    mock_collection = MagicMock()
    mock_collection.server_info = MagicMock(return_value={"version": "2.0.0"})
    mock_collection.schema = MagicMock()
    mock_collection.schema.primary_field = MagicMock(return_value="id")

    mock_handler = MagicMock()
    mock_handler.has_collection = MagicMock(return_value=True)
    mock_handler.describe_collection = MagicMock(return_value={
        "fields": [
            {"name": "id", "type": 5, "is_primary": True},
            {"name": "vector", "type": 101, "params": {"dim": 128}}
        ]
    })

    with patch('pymilvus.connections.connect') as mock_connect, \
         patch('pymilvus.Collection', return_value=mock_collection), \
         patch('pymilvus.connections._fetch_handler', return_value=mock_handler):
        await vector_service.initialize()
        assert vector_service.is_initialized
        mock_connect.assert_called_once()

@pytest.mark.asyncio
async def test_vector_service_initialize_failure(vector_service):
    """Test initialization failure."""
    with patch('pymilvus.connections.connect', side_effect=Exception("Connection failed")):
        with pytest.raises(MCPError) as exc_info:
            await vector_service.initialize()
        assert "Connection failed" in str(exc_info.value)
        assert not vector_service._initialized

@pytest.mark.asyncio
async def test_vector_service_shutdown_success(vector_service):
    """Test successful shutdown."""
    vector_service._initialized = True
    vector_service._client = MagicMock()
    
    with patch('pymilvus.connections.disconnect') as mock_disconnect:
        await vector_service.shutdown()
        mock_disconnect.assert_called_once_with("default")
        assert vector_service._client is None

@pytest.mark.asyncio
async def test_vector_service_shutdown_failure(vector_service):
    """Test shutdown failure."""
    vector_service._initialized = True
    vector_service._client = MagicMock()
    
    with patch('pymilvus.connections.disconnect', side_effect=Exception("Disconnect failed")):
        with pytest.raises(MCPError) as exc_info:
            await vector_service.shutdown()
        assert "Disconnect failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_vector_service_search_success(vector_service):
    """Test successful vector search."""
    mock_hit = MagicMock()
    mock_hit.id = "1"
    mock_hit.distance = 0.5
    
    vector_service._client = MagicMock()
    vector_service._initialized = True
    vector_service._client.search.return_value = [[mock_hit]]
    
    result = await vector_service.search([0.1, 0.2, 0.3], 10)
    assert result == [{"id": "1", "distance": 0.5}]

@pytest.mark.asyncio
async def test_vector_service_search_no_results(vector_service):
    """Test vector search with no results."""
    vector_service._client = MagicMock(spec=Collection)
    vector_service._initialized = True
    vector_service._client.search.return_value = []

    result = await vector_service.search([0.1, 0.2, 0.3], 10)
    assert result == []

@pytest.mark.asyncio
async def test_vector_service_search_not_initialized(vector_service):
    """Test search when service is not initialized."""
    with pytest.raises(MCPError) as exc_info:
        await vector_service.search([0.1, 0.2, 0.3], 10)
    assert "Service must be initialized before use" in str(exc_info.value)

@pytest.mark.asyncio
async def test_vector_service_search_failure(vector_service):
    """Test search failure."""
    vector_service._client = MagicMock(spec=Collection)
    vector_service._initialized = True
    vector_service._client.search.side_effect = Exception("Search failed")

    with pytest.raises(MCPError) as exc_info:
        await vector_service.search([0.1, 0.2, 0.3], 10)
    assert "Search failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_vector_service_health_check_success(vector_service):
    """Test successful health check."""
    vector_service._client = MagicMock()
    vector_service._initialized = True
    vector_service._client.server_info = MagicMock(return_value={"version": "2.0.0"})
    
    health = await vector_service.health_check()
    assert health["status"] == "ok"
    assert health["version"] == "2.0.0"

@pytest.mark.asyncio
async def test_vector_service_health_check_not_initialized(vector_service):
    """Test health check when service is not initialized."""
    result = await vector_service.health_check()
    assert result["status"] == "not_initialized"

@pytest.mark.asyncio
async def test_vector_service_health_check_failure(vector_service):
    """Test health check failure."""
    vector_service._client = MagicMock()
    vector_service._initialized = True
    vector_service._client.server_info = MagicMock(side_effect=Exception("Version check failed"))
    
    health = await vector_service.health_check()
    assert health["status"] == "error"
    assert "Version check failed" in health["message"] 

@pytest.mark.asyncio
async def test_create_client_connection_error(vector_service):
    """Test client creation with connection error."""
    with patch('pymilvus.connections.connect', side_effect=Exception("Connection error")):
        with pytest.raises(MCPError) as exc_info:
            vector_service._create_client()
        assert exc_info.value.code == "INIT_ERROR"
        assert "Connection error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_create_client_collection_error(vector_service):
    """Test client creation with collection error."""
    with patch('pymilvus.connections.connect') as mock_connect, \
         patch('pymilvus.Collection', side_effect=ConnectionNotExistException("should create connection first")):
        with pytest.raises(MCPError) as exc_info:
            vector_service._create_client()
        assert exc_info.value.code == "INIT_ERROR"
        assert "should create connection first" in str(exc_info.value)
        mock_connect.assert_called_once()

@pytest.mark.asyncio
async def test_initialize_client_creation_error(vector_service):
    """Test initialization with client creation error."""
    with patch.object(vector_service, '_create_client', side_effect=MCPError("INIT_ERROR", "Client creation failed")):
        with pytest.raises(MCPError) as exc_info:
            await vector_service.initialize()
        assert exc_info.value.code == "INIT_ERROR"
        assert "Client creation failed" in str(exc_info.value)
        assert not vector_service._initialized

@pytest.mark.asyncio
async def test_search_invalid_vector(vector_service):
    """Test search with invalid vector."""
    vector_service._client = MagicMock()
    vector_service._initialized = True
    
    # Test with empty vector
    with pytest.raises(MCPError) as exc_info:
        await vector_service.search([], 10)
    assert "Vector cannot be empty" in str(exc_info.value)
    
    # Test with invalid vector type
    with pytest.raises(MCPError) as exc_info:
        await vector_service.search("not a vector", 10)
    assert "Invalid vector type" in str(exc_info.value)

@pytest.mark.asyncio
async def test_search_invalid_top_k(vector_service):
    """Test search with invalid top_k."""
    vector_service._client = MagicMock()
    vector_service._initialized = True
    
    # Test with negative top_k
    with pytest.raises(MCPError) as exc_info:
        await vector_service.search([0.1, 0.2], -1)
    assert "top_k must be positive" in str(exc_info.value)
    
    # Test with zero top_k
    with pytest.raises(MCPError) as exc_info:
        await vector_service.search([0.1, 0.2], 0)
    assert "top_k must be positive" in str(exc_info.value)

@pytest.mark.asyncio
async def test_search_with_multiple_results(vector_service):
    """Test search with multiple results."""
    mock_hits = [
        MagicMock(id="1", distance=0.5),
        MagicMock(id="2", distance=0.7),
        MagicMock(id="3", distance=0.9)
    ]
    
    vector_service._client = MagicMock()
    vector_service._initialized = True
    vector_service._client.search.return_value = [mock_hits]
    
    result = await vector_service.search([0.1, 0.2, 0.3], 3)
    assert len(result) == 3
    assert result[0] == {"id": "1", "distance": 0.5}
    assert result[1] == {"id": "2", "distance": 0.7}
    assert result[2] == {"id": "3", "distance": 0.9}

@pytest.mark.asyncio
async def test_search_with_limit(vector_service):
    """Test search with result limit."""
    mock_hits = [
        MagicMock(id="1", distance=0.5),
        MagicMock(id="2", distance=0.7)
    ]
    
    vector_service._client = MagicMock()
    vector_service._initialized = True
    
    # Request more results than available
    vector_service._client.search.return_value = [mock_hits]
    result = await vector_service.search([0.1, 0.2, 0.3], 5)
    assert len(result) == 2
    
    # Request fewer results than available
    vector_service._client.search.return_value = [mock_hits[:1]]  # Only return first hit
    result = await vector_service.search([0.1, 0.2, 0.3], 1)
    assert len(result) == 1
    assert result[0] == {"id": "1", "distance": 0.5} 

@pytest.mark.asyncio
async def test_initialize_when_already_initialized(vector_service):
    """Test initialization when service is already initialized."""
    mock_collection = MagicMock()
    mock_collection.server_info = MagicMock(return_value={"version": "2.0.0"})
    mock_collection.schema = MagicMock()
    mock_collection.schema.primary_field = MagicMock(return_value="id")

    mock_handler = MagicMock()
    mock_handler.has_collection = MagicMock(return_value=True)
    mock_handler.describe_collection = MagicMock(return_value={
        "fields": [
            {"name": "id", "type": 5, "is_primary": True},
            {"name": "vector", "type": 101, "params": {"dim": 128}}
        ]
    })
    
    with patch('pymilvus.connections.connect') as mock_connect, \
         patch('pymilvus.Collection', return_value=mock_collection), \
         patch('pymilvus.connections._fetch_handler', return_value=mock_handler):
        # First initialization
        await vector_service.initialize()
        assert vector_service.is_initialized
        first_client = vector_service._client
        
        # Second initialization should return early
        await vector_service.initialize()
        assert vector_service.is_initialized
        assert vector_service._client is first_client  # Client should not be recreated
        mock_connect.assert_called_once()  # Connect should only be called once

@pytest.mark.asyncio
async def test_search_with_non_numeric_vector(vector_service):
    """Test search with vector containing non-numeric values."""
    vector_service._client = MagicMock()
    vector_service._initialized = True
    
    with pytest.raises(MCPError) as exc_info:
        await vector_service.search([0.1, "not a number", 0.3], 10)
    assert "Vector must contain only numbers" in str(exc_info.value)
    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.details == {"vector": [0.1, "not a number", 0.3]}

@pytest.mark.asyncio
async def test_search_with_empty_results_list(vector_service):
    """Test search when results[0] is empty."""
    vector_service._client = MagicMock()
    vector_service._initialized = True
    vector_service._client.search.return_value = [[]]  # Empty results[0]
    
    result = await vector_service.search([0.1, 0.2, 0.3], 10)
    assert result == [] 

@pytest.mark.asyncio
async def test_search_with_invalid_vector_type(vector_service):
    """Test search with invalid vector type (not a list)."""
    vector_service._client = MagicMock()
    vector_service._initialized = True
    
    # Test with non-list vector
    with pytest.raises(MCPError) as exc_info:
        await vector_service.search("not a list", 10)
    assert "Invalid vector type" in str(exc_info.value)
    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.details == {"vector": "not a list"} 

@pytest.mark.asyncio
async def test_vector_service_initialize_generic_error(vector_service):
    """Test initialization with a generic error."""
    mock_collection = MagicMock()
    mock_collection.server_info = MagicMock(side_effect=RuntimeError("Server error"))
    
    with patch('pymilvus.connections.connect') as mock_connect, \
         patch('pymilvus.Collection', return_value=mock_collection):
        mock_connect.side_effect = RuntimeError("Server error")
        with pytest.raises(MCPError) as exc_info:
            await vector_service.initialize()
        assert "Server error" in str(exc_info.value)
        assert exc_info.value.code == "INIT_ERROR"
        assert not vector_service._initialized 

@pytest.mark.asyncio
async def test_vector_service_initialize_mcp_error(vector_service):
    """Test initialization with an MCPError."""
    with patch.object(vector_service, '_create_client', side_effect=MCPError("TEST_ERROR", "Test error")):
        with pytest.raises(MCPError) as exc_info:
            await vector_service.initialize()
        assert "Test error" in str(exc_info.value)
        assert exc_info.value.code == "TEST_ERROR"
        assert not vector_service._initialized 

@pytest.mark.asyncio
async def test_vector_service_initialize_inner_mcp_error(vector_service):
    """Test initialization with an MCPError raised from within initialize."""
    test_error = MCPError("TEST_ERROR", "Test error")
    
    with patch('pymilvus.connections.connect') as mock_connect:
        mock_connect.side_effect = test_error
        with pytest.raises(MCPError) as exc_info:
            await vector_service.initialize()
        assert "Test error" in str(exc_info.value)
        assert exc_info.value.code == "TEST_ERROR"
        assert not vector_service._initialized 

@pytest.mark.asyncio
async def test_initialize_general_exception(mocker, vector_service):
    """Test initialization failure with a general exception."""
    # Mock the create client to raise a general exception
    mocker.patch.object(
        vector_service,
        '_create_client',
        side_effect=Exception("General error")
    )
    
    with pytest.raises(MCPError) as exc_info:
        await vector_service.initialize()
    
    assert exc_info.value.code == "INIT_ERROR"
    assert "Failed to initialize vector service" in str(exc_info.value)
    assert not vector_service.is_initialized 