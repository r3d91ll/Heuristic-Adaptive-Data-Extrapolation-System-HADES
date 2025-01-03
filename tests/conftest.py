"""Test configuration and fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from hades.core.config import DatabaseConfig, MilvusConfig, ServerConfig
from hades.services.database import DatabaseService
from hades.services.vector import VectorService
from hades.services.hybrid import HybridSearchService


@pytest.fixture
def database_config():
    """Return a mock database configuration."""
    return DatabaseConfig(
        host="localhost",
        port=8529,
        username="root",
        password="password",
        database="_system"
    )


@pytest.fixture
def milvus_config():
    """Return a mock Milvus configuration."""
    return MilvusConfig(
        host="localhost",
        port=19530,
        user="root",
        password="password",
        collection="test_collection"
    )


@pytest.fixture
def server_config():
    """Return a mock server configuration."""
    return ServerConfig(
        host="localhost",
        port=8080
    )


@pytest.fixture
def mock_arango_client():
    """Return a mock ArangoDB client."""
    client = MagicMock()
    client.db = MagicMock()
    client.db.aql = MagicMock()
    client.db.aql.execute = AsyncMock()
    return client


@pytest.fixture
def mock_milvus_client():
    """Return a mock Milvus client."""
    client = MagicMock()
    client.search = AsyncMock()
    client.server_info = MagicMock(return_value={"version": "2.0.0"})
    client.id = MagicMock(return_value="test_id")
    client.distance = MagicMock(return_value=0.5)
    return client


@pytest.fixture
def database_service(database_config, mock_arango_client):
    """Return a database service with mocked client."""
    service = DatabaseService(database_config)
    service._client = mock_arango_client
    return service


@pytest.fixture
def vector_service(milvus_config, mock_milvus_client):
    """Return a vector service with mocked client."""
    service = VectorService(milvus_config)
    service._client = mock_milvus_client
    return service


@pytest.fixture
def hybrid_service(database_service, vector_service):
    """Return a hybrid search service with mocked dependencies."""
    return HybridSearchService(database_service, vector_service) 