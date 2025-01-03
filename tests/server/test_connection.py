"""Tests for the connection manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from hades.core.config import DatabaseConfig, MilvusConfig
from hades.core.exceptions import MCPError
from hades.server.connection import ConnectionManager

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
def milvus_config():
    """Create a Milvus configuration for testing."""
    return MilvusConfig(
        host="test-host",
        port=19530,
        user="test-user",
        password="test-pass",
        collection="test-collection"
    )

@pytest.fixture
def connection_manager(database_config, milvus_config):
    """Create a connection manager instance for testing."""
    manager = ConnectionManager(database_config, milvus_config)
    manager.db_service = MagicMock()
    manager.vector_service = MagicMock()
    return manager

@pytest.mark.asyncio
async def test_connection_manager_initialization(database_config, milvus_config):
    """Test connection manager initialization."""
    manager = ConnectionManager(database_config, milvus_config)
    assert manager.retry_delay == 1.0
    assert manager.max_retries == 3
    assert manager.db_service is not None
    assert manager.vector_service is not None

@pytest.mark.asyncio
async def test_connection_manager_initialize_success(connection_manager):
    """Test successful initialization."""
    connection_manager.db_service.initialize = AsyncMock()
    connection_manager.vector_service.initialize = AsyncMock()
    
    await connection_manager.initialize()
    connection_manager.db_service.initialize.assert_called_once()
    connection_manager.vector_service.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_connection_manager_initialize_failure(connection_manager):
    """Test initialization failure."""
    connection_manager.db_service.initialize = AsyncMock(side_effect=Exception("DB init failed"))
    connection_manager.vector_service.initialize = AsyncMock()
    
    with pytest.raises(MCPError) as exc_info:
        await connection_manager.initialize()
    assert "DB init failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_connection_manager_shutdown_success(connection_manager):
    """Test successful shutdown."""
    connection_manager.db_service.shutdown = AsyncMock()
    connection_manager.vector_service.shutdown = AsyncMock()
    
    await connection_manager.shutdown()
    connection_manager.db_service.shutdown.assert_called_once()
    connection_manager.vector_service.shutdown.assert_called_once()

@pytest.mark.asyncio
async def test_connection_manager_shutdown_handles_errors(connection_manager):
    """Test shutdown error handling."""
    connection_manager.db_service.shutdown = AsyncMock(side_effect=Exception("DB shutdown failed"))
    connection_manager.vector_service.shutdown = AsyncMock()
    
    with pytest.raises(MCPError) as exc_info:
        await connection_manager.shutdown()
    assert "DB shutdown failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_connection_manager_health_check_all_ok(connection_manager):
    """Test health check when all services are ok."""
    connection_manager._initialized = True
    connection_manager.db_service.health_check = AsyncMock(return_value={"status": "ok"})
    connection_manager.vector_service.health_check = AsyncMock(return_value={"status": "ok"})
    
    health = await connection_manager.health_check()
    assert health["status"] == "ok"

@pytest.mark.asyncio
async def test_connection_manager_health_check_degraded(connection_manager):
    """Test health check when some services are degraded."""
    connection_manager._initialized = True
    connection_manager.db_service.health_check = AsyncMock(return_value={"status": "ok"})
    connection_manager.vector_service.health_check = AsyncMock(return_value={"status": "error"})
    
    health = await connection_manager.health_check()
    assert health["status"] == "degraded"

@pytest.mark.asyncio
async def test_connection_manager_shutdown_multiple_errors(connection_manager):
    """Test shutdown when both services fail."""
    connection_manager.db_service.shutdown = AsyncMock(side_effect=Exception("DB shutdown failed"))
    connection_manager.vector_service.shutdown = AsyncMock(side_effect=Exception("Vector shutdown failed"))
    
    with pytest.raises(MCPError) as exc_info:
        await connection_manager.shutdown()
    assert "DB shutdown failed" in str(exc_info.value)
    assert not connection_manager._initialized

@pytest.mark.asyncio
async def test_connection_manager_health_check_not_initialized(connection_manager):
    """Test health check when not initialized."""
    connection_manager._initialized = False
    health = await connection_manager.health_check()
    assert health["status"] == "not_initialized"

@pytest.mark.asyncio
async def test_connection_manager_health_check_error(connection_manager):
    """Test health check when an error occurs."""
    connection_manager._initialized = True
    connection_manager.db_service.health_check = AsyncMock(side_effect=Exception("Health check failed"))
    
    health = await connection_manager.health_check()
    assert health["status"] == "error"
    assert "Health check failed" in health["message"] 