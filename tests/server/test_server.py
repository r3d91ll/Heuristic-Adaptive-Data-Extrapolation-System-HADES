"""Tests for the server module."""

import pytest
import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from hades.core.config import ServerConfig, DatabaseConfig, MilvusConfig
from hades.core.exceptions import MCPError
from hades.server.server import MCPServer
from hades.server.connection import ConnectionManager
from hades.services.hybrid import HybridSearchService

@pytest.fixture
def server_config():
    """Create a server configuration for testing."""
    return ServerConfig(
        host="test-host",
        port=8080,
        thread_pool_size=5
    )

@pytest.fixture
def db_config():
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
def mock_connection_manager():
    """Create a mock connection manager."""
    manager = AsyncMock(spec=ConnectionManager)
    manager.initialize = AsyncMock()
    manager.shutdown = AsyncMock()
    manager.health_check = AsyncMock(return_value={"status": "ok"})
    manager.db_service = AsyncMock()
    manager.vector_service = AsyncMock()
    return manager

@pytest.fixture
def server(server_config, db_config, milvus_config, mock_connection_manager):
    """Create a server instance for testing."""
    server = MCPServer(server_config, db_config, milvus_config)
    server.conn_manager = mock_connection_manager
    server._executor = MagicMock()
    return server

def test_server_initialization(server_config, db_config, milvus_config):
    """Test server initialization."""
    server = MCPServer(server_config, db_config, milvus_config)
    assert server.name == "mcp-server"
    assert server.server_config == server_config
    assert server.db_config == db_config
    assert server.milvus_config == milvus_config
    assert server.start_time > 0

def test_server_initialization_defaults():
    """Test server initialization with default configs."""
    server = MCPServer(
        ServerConfig(host="test-host"),
        DatabaseConfig(
            host="test-host",
            username="test-user",
            password="test-pass"
        ),
        MilvusConfig(
            host="test-host",
            user="test-user",
            password="test-pass",
            collection="test-collection"
        )
    )
    assert isinstance(server.server_config, ServerConfig)
    assert isinstance(server.db_config, DatabaseConfig)
    assert isinstance(server.milvus_config, MilvusConfig)
    assert server.start_time > 0

@pytest.mark.asyncio
async def test_server_initialize_success(server, mock_connection_manager):
    """Test successful server initialization."""
    mock_hybrid_service = AsyncMock(spec=HybridSearchService)
    
    with patch('hades.server.server.HybridSearchService', return_value=mock_hybrid_service):
        await server.initialize()
    
    mock_connection_manager.initialize.assert_called_once()
    mock_hybrid_service.initialize.assert_called_once()
    assert server.handler is not None

@pytest.mark.asyncio
async def test_server_initialize_connection_failure(server, mock_connection_manager):
    """Test server initialization with connection failure."""
    mock_connection_manager.initialize.side_effect = Exception("Connection failed")
    
    with pytest.raises(MCPError) as exc_info:
        await server.initialize()
    
    assert exc_info.value.code == "SERVER_INIT_ERROR"
    assert "Connection failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_server_initialize_hybrid_failure(server, mock_connection_manager):
    """Test server initialization with hybrid service failure."""
    mock_hybrid_service = AsyncMock(spec=HybridSearchService)
    mock_hybrid_service.initialize.side_effect = Exception("Hybrid init failed")
    
    with patch('hades.server.server.HybridSearchService', return_value=mock_hybrid_service), \
         pytest.raises(MCPError) as exc_info:
        await server.initialize()
    
    assert exc_info.value.code == "SERVER_INIT_ERROR"
    assert "Hybrid init failed" in str(exc_info.value)

def test_server_close(server):
    """Test server cleanup."""
    server.close()
    server._executor.shutdown.assert_called_once_with(wait=True)

def test_server_close_handles_errors(server):
    """Test server cleanup with errors."""
    server._executor.shutdown.side_effect = Exception("Shutdown failed")
    
    # Should not raise exception
    server.close()

def test_server_signal_handling(server):
    """Test server signal handling."""
    with patch('sys.exit') as mock_exit:
        # Test SIGINT
        server._handle_shutdown(signal.SIGINT, None)
        server._executor.shutdown.assert_called_once_with(wait=True)
        mock_exit.assert_called_once_with(0)
        
        # Reset mocks
        server._executor.shutdown.reset_mock()
        mock_exit.reset_mock()
        
        # Test SIGTERM
        server._handle_shutdown(signal.SIGTERM, None)
        server._executor.shutdown.assert_called_once_with(wait=True)
        mock_exit.assert_called_once_with(0)

@pytest.mark.asyncio
async def test_server_handle_request_success(server):
    """Test successful request handling."""
    mock_request = MagicMock()
    mock_handler = AsyncMock()
    mock_handler.handle_request.return_value = {"success": True, "result": "test"}
    server.handler = mock_handler
    
    response = await server.handle_request(mock_request)
    assert response["success"] is True
    assert response["result"] == "test"
    mock_handler.handle_request.assert_called_once_with(mock_request)

@pytest.mark.asyncio
async def test_server_handle_request_error(server):
    """Test request handling with error."""
    mock_request = MagicMock()
    mock_handler = AsyncMock()
    mock_handler.handle_request.side_effect = Exception("Request failed")
    server.handler = mock_handler
    
    response = await server.handle_request(mock_request)
    assert response["success"] is False
    assert response["error"]["code"] == "REQUEST_ERROR"
    assert "Request failed" in response["error"]["message"]

@pytest.mark.asyncio
async def test_server_health_check_success(server, mock_connection_manager):
    """Test successful health check."""
    server.start_time = 0  # Reset start time for predictable testing
    
    health = await server.health_check()
    assert health["status"] == "ok"
    assert "uptime" in health
    assert health["uptime"] >= 0
    assert health["connections"]["status"] == "ok"

@pytest.mark.asyncio
async def test_server_health_check_degraded(server, mock_connection_manager):
    """Test health check with degraded status."""
    mock_connection_manager.health_check.return_value = {"status": "degraded"}
    
    health = await server.health_check()
    assert health["status"] == "degraded"

@pytest.mark.asyncio
async def test_server_health_check_error(server, mock_connection_manager):
    """Test health check with error."""
    mock_connection_manager.health_check.side_effect = Exception("Health check failed")
    
    health = await server.health_check()
    assert health["status"] == "error"
    assert "Health check failed" in health["error"] 