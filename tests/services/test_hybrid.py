"""Tests for the hybrid search service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from hades.core.config import HybridSearchConfig
from hades.core.exceptions import MCPError
from hades.services.hybrid import HybridSearchService
from hades.services.database import DatabaseService
from hades.services.vector import VectorService

@pytest.fixture
def hybrid_config():
    """Create a test hybrid search config."""
    return HybridSearchConfig(
        collection="test_collection",
        vector_field="vector",
        text_field="text",
        id_field="_id"
    )

@pytest.fixture
def mock_db_service():
    """Create a mock database service."""
    service = MagicMock(spec=DatabaseService)
    service.execute_query = AsyncMock()
    return service

@pytest.fixture
def mock_vector_service():
    """Create a mock vector service."""
    service = MagicMock(spec=VectorService)
    service.search = AsyncMock()
    return service

@pytest.fixture
def hybrid_service(hybrid_config, mock_db_service, mock_vector_service):
    """Create a test hybrid search service."""
    return HybridSearchService(
        config=hybrid_config,
        db_service=mock_db_service,
        vector_service=mock_vector_service
    )

@pytest.mark.asyncio
async def test_initialize_success(hybrid_service):
    """Test successful initialization."""
    await hybrid_service.initialize()
    assert hybrid_service._initialized

@pytest.mark.asyncio
async def test_initialize_db_service_error(hybrid_service, mock_db_service):
    """Test initialization with database service error."""
    mock_db_service.initialize.side_effect = MCPError("INIT_ERROR", "DB init failed")
    
    with pytest.raises(MCPError) as exc_info:
        await hybrid_service.initialize()
    assert exc_info.value.code == "INIT_ERROR"
    assert "DB init failed" in str(exc_info.value)
    assert not hybrid_service._initialized

@pytest.mark.asyncio
async def test_initialize_vector_service_error(hybrid_service, mock_vector_service):
    """Test initialization with vector service error."""
    mock_vector_service.initialize.side_effect = MCPError("INIT_ERROR", "Vector init failed")
    
    with pytest.raises(MCPError) as exc_info:
        await hybrid_service.initialize()
    assert exc_info.value.code == "INIT_ERROR"
    assert "Vector init failed" in str(exc_info.value)
    assert not hybrid_service._initialized

@pytest.mark.asyncio
async def test_search_success(hybrid_service, mock_db_service, mock_vector_service):
    """Test successful hybrid search."""
    hybrid_service._initialized = True
    vector = [0.1, 0.2, 0.3]
    filter_query = "doc.type == 'test'"
    top_k = 5
    
    mock_vector_service.search.return_value = [
        {"_id": "1", "score": 0.9},
        {"_id": "2", "score": 0.8}
    ]
    
    mock_db_service.execute_query.return_value = [
        {"_id": "1", "text": "test1"},
        {"_id": "2", "text": "test2"}
    ]
    
    results = await hybrid_service.search(vector, filter_query, top_k)
    
    assert len(results) == 2
    assert results[0]["_id"] == "1"
    assert results[1]["_id"] == "2"
    assert "score" in results[0]
    assert "text" in results[0]

@pytest.mark.asyncio
async def test_search_not_initialized(hybrid_service):
    """Test search when service is not initialized."""
    with pytest.raises(MCPError) as exc_info:
        await hybrid_service.search([0.1], "test", 5)
    assert exc_info.value.code == "NOT_INITIALIZED"
    assert "not initialized" in str(exc_info.value)

@pytest.mark.asyncio
async def test_search_empty_vector(hybrid_service):
    """Test search with empty vector."""
    hybrid_service._initialized = True
    
    with pytest.raises(MCPError) as exc_info:
        await hybrid_service.search([], "test", 5)
    assert exc_info.value.code == "VALIDATION_ERROR"
    assert "vector cannot be empty" in str(exc_info.value)

@pytest.mark.asyncio
async def test_search_invalid_top_k(hybrid_service):
    """Test search with invalid top_k."""
    hybrid_service._initialized = True
    
    with pytest.raises(MCPError) as exc_info:
        await hybrid_service.search([0.1], "test", 0)
    assert exc_info.value.code == "VALIDATION_ERROR"
    assert "top_k must be positive" in str(exc_info.value)

@pytest.mark.asyncio
async def test_search_vector_service_error(hybrid_service, mock_vector_service):
    """Test search with vector service error."""
    hybrid_service._initialized = True
    mock_vector_service.search.side_effect = MCPError("SEARCH_ERROR", "Vector search failed")
    
    with pytest.raises(MCPError) as exc_info:
        await hybrid_service.search([0.1], "test", 5)
    assert exc_info.value.code == "SEARCH_ERROR"
    assert "Vector search failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_search_db_service_error(hybrid_service, mock_db_service, mock_vector_service):
    """Test search with database service error."""
    hybrid_service._initialized = True
    mock_vector_service.search.return_value = [{"_id": "1", "score": 0.9}]
    mock_db_service.execute_query.side_effect = MCPError("QUERY_ERROR", "Query failed")
    
    with pytest.raises(MCPError) as exc_info:
        await hybrid_service.search([0.1], "test", 5)
    assert exc_info.value.code == "QUERY_ERROR"
    assert "Query failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_health_check_success(hybrid_service, mock_db_service, mock_vector_service):
    """Test successful health check."""
    hybrid_service._initialized = True
    mock_db_service.health_check.return_value = {"status": "ok", "message": "DB healthy"}
    mock_vector_service.health_check.return_value = {"status": "ok", "message": "Vector healthy"}
    
    health = await hybrid_service.health_check()
    
    assert health["status"] == "ok"
    assert "DB healthy" in health["message"]
    assert "Vector healthy" in health["message"]

@pytest.mark.asyncio
async def test_health_check_not_initialized(hybrid_service):
    """Test health check when service is not initialized."""
    health = await hybrid_service.health_check()
    
    assert health["status"] == "error"
    assert "not initialized" in health["message"]

@pytest.mark.asyncio
async def test_health_check_db_error(hybrid_service):
    """Test health check with database service error."""
    hybrid_service._initialized = True
    hybrid_service._db_service.health_check.return_value = {"status": "error", "message": "DB error"}
    hybrid_service._vector_service.health_check.return_value = {"status": "ok", "message": "Vector healthy"}

    health = await hybrid_service.health_check()

    assert health["status"] == "error"
    assert "DB error" in health["message"]
    assert "Vector healthy" in health["message"]

@pytest.mark.asyncio
async def test_health_check_vector_error(hybrid_service):
    """Test health check with vector service error."""
    hybrid_service._initialized = True
    hybrid_service._db_service.health_check.return_value = {"status": "ok", "message": "DB healthy"}
    hybrid_service._vector_service.health_check.return_value = {"status": "error", "message": "Vector error"}

    health = await hybrid_service.health_check()

    assert health["status"] == "error"
    assert "DB healthy" in health["message"]
    assert "Vector error" in health["message"]

@pytest.mark.asyncio
async def test_initialize_already_initialized(hybrid_service):
    """Test initialization when already initialized."""
    hybrid_service._initialized = True
    await hybrid_service.initialize()  # Should return early
    assert hybrid_service._initialized

@pytest.mark.asyncio
async def test_initialize_generic_error(hybrid_service, mock_db_service):
    """Test initialization with a generic error."""
    mock_db_service.initialize.side_effect = ValueError("Unexpected error")
    
    with pytest.raises(MCPError) as exc_info:
        await hybrid_service.initialize()
    assert exc_info.value.code == "INIT_ERROR"
    assert "Unexpected error" in str(exc_info.value)
    assert not hybrid_service._initialized

@pytest.mark.asyncio
async def test_search_empty_vector_results(hybrid_service, mock_vector_service):
    """Test search when vector service returns empty results."""
    hybrid_service._initialized = True
    mock_vector_service.search.return_value = []
    
    results = await hybrid_service.search([0.1], "test", 5)
    assert results == []
    # Verify that database query was not called
    hybrid_service._db_service.execute_query.assert_not_called()

@pytest.mark.asyncio
async def test_search_generic_error(hybrid_service, mock_vector_service):
    """Test search with a generic error."""
    hybrid_service._initialized = True
    mock_vector_service.search.side_effect = ValueError("Unexpected error")
    
    with pytest.raises(MCPError) as exc_info:
        await hybrid_service.search([0.1], "test", 5)
    assert exc_info.value.code == "SEARCH_ERROR"
    assert "Unexpected error" in str(exc_info.value)
    assert "vector" in exc_info.value.details
    assert "filter_query" in exc_info.value.details
    assert "top_k" in exc_info.value.details

@pytest.mark.asyncio
async def test_health_check_generic_error(hybrid_service, mock_db_service):
    """Test health check with a generic error."""
    hybrid_service._initialized = True
    mock_db_service.health_check.side_effect = ValueError("Unexpected error")
    
    health = await hybrid_service.health_check()
    assert health["status"] == "error"
    assert "Unexpected error" in health["message"] 