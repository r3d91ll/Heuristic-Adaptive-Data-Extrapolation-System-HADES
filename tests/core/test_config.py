"""Tests for configuration classes."""

import pytest
from pydantic import ValidationError
from hades.core.config import (
    DatabaseConfig, MilvusConfig, ServerConfig, HybridSearchConfig,
    MemoryConfig, Config
)

def test_database_config_defaults():
    """Test database configuration with default values."""
    config = DatabaseConfig(
        host="localhost",
        port=8529,
        username="root",
        password="password",
        database="_system"
    )
    assert config.host == "localhost"
    assert config.port == 8529
    assert config.username == "root"
    assert config.password == "password"
    assert config.database == "_system"

def test_database_config_validation():
    """Test database configuration validation."""
    with pytest.raises(ValidationError):
        DatabaseConfig(
            host="",  # Empty host not allowed
            port=8529,
            username="root",
            password="password",
            database="_system"
        )

    with pytest.raises(ValidationError):
        DatabaseConfig(
            host="localhost",
            port=-1,  # Invalid port
            username="root",
            password="password",
            database="_system"
        )

def test_milvus_config_defaults():
    """Test Milvus configuration with default values."""
    config = MilvusConfig(
        host="localhost",
        port=19530,
        user="root",
        password="password",
        collection="test_collection"
    )
    assert config.host == "localhost"
    assert config.port == 19530
    assert config.user == "root"
    assert config.password == "password"
    assert config.collection == "test_collection"

def test_milvus_config_validation():
    """Test Milvus configuration validation."""
    with pytest.raises(ValidationError):
        MilvusConfig(
            host="",  # Empty host not allowed
            port=19530,
            user="root",
            password="password",
            collection="test_collection"
        )

    with pytest.raises(ValidationError):
        MilvusConfig(
            host="localhost",
            port=-1,  # Invalid port
            user="root",
            password="password",
            collection="test_collection"
        )

def test_server_config_defaults():
    """Test server configuration with default values."""
    config = ServerConfig(
        host="localhost",
        port=8080
    )
    assert config.host == "localhost"
    assert config.port == 8080

def test_server_config_validation():
    """Test server configuration validation."""
    with pytest.raises(ValidationError):
        ServerConfig(
            host="",  # Empty host not allowed
            port=8080
        )

    with pytest.raises(ValidationError):
        ServerConfig(
            host="localhost",
            port=-1  # Invalid port
        ) 

def test_hybrid_search_config_defaults():
    """Test hybrid search configuration with default values."""
    config = HybridSearchConfig()
    assert config.collection == "documents"
    assert config.vector_field == "vector"
    assert config.text_field == "text"
    assert config.id_field == "_id"
    assert config.min_score == 0.0
    assert config.max_results == 10

def test_hybrid_search_config_validation_success():
    """Test hybrid search configuration successful validation."""
    config = HybridSearchConfig(
        collection="test_collection",
        vector_field="test_vector",
        text_field="test_text",
        id_field="test_id",
        min_score=0.5,
        max_results=20
    )
    assert config.collection == "test_collection"
    assert config.vector_field == "test_vector"
    assert config.text_field == "test_text"
    assert config.id_field == "test_id"
    assert config.min_score == 0.5
    assert config.max_results == 20

def test_hybrid_search_config_validation():
    """Test hybrid search configuration validation."""
    # Test empty collection name
    with pytest.raises(ValidationError) as exc_info:
        HybridSearchConfig(collection="")
    assert "Collection name cannot be empty" in str(exc_info.value)

    # Test empty vector field
    with pytest.raises(ValidationError) as exc_info:
        HybridSearchConfig(vector_field="")
    assert "Vector field name cannot be empty" in str(exc_info.value)

    # Test empty text field
    with pytest.raises(ValidationError) as exc_info:
        HybridSearchConfig(text_field="")
    assert "Text field name cannot be empty" in str(exc_info.value)

    # Test empty ID field
    with pytest.raises(ValidationError) as exc_info:
        HybridSearchConfig(id_field="")
    assert "ID field name cannot be empty" in str(exc_info.value)

    # Test invalid min_score (negative)
    with pytest.raises(ValidationError) as exc_info:
        HybridSearchConfig(min_score=-0.1)
    assert "Minimum score must be between 0 and 1" in str(exc_info.value)

    # Test invalid min_score (greater than 1)
    with pytest.raises(ValidationError) as exc_info:
        HybridSearchConfig(min_score=1.1)
    assert "Minimum score must be between 0 and 1" in str(exc_info.value)

    # Test invalid max_results (zero)
    with pytest.raises(ValidationError) as exc_info:
        HybridSearchConfig(max_results=0)
    assert "Maximum results must be positive" in str(exc_info.value)

    # Test invalid max_results (negative)
    with pytest.raises(ValidationError) as exc_info:
        HybridSearchConfig(max_results=-1)
    assert "Maximum results must be positive" in str(exc_info.value)

def test_server_config_thread_pool_validation():
    """Test server configuration thread pool validation."""
    # Test valid thread pool size
    config = ServerConfig(thread_pool_size=4)
    assert config.thread_pool_size == 4

    # Test zero thread pool size
    with pytest.raises(ValidationError) as exc_info:
        ServerConfig(thread_pool_size=0)
    assert "Thread pool size must be positive" in str(exc_info.value)

    # Test negative thread pool size
    with pytest.raises(ValidationError) as exc_info:
        ServerConfig(thread_pool_size=-1)
    assert "Thread pool size must be positive" in str(exc_info.value)

def test_memory_config_defaults():
    """Test memory configuration with default values."""
    config = MemoryConfig()
    assert config.elysium_capacity == 1000
    assert config.asphodel_window == 2000
    assert config.lethe_threshold == 0.5
    assert config.enable_archival is True

def test_main_config_defaults():
    """Test main configuration with default values."""
    config = Config()
    assert isinstance(config.memory, MemoryConfig)
    assert isinstance(config.hybrid_search, HybridSearchConfig)

def test_main_config_env_settings():
    """Test main configuration with environment settings."""
    # Note: This test is just to verify the model_config settings
    # Actual environment variable testing would require setting up test environment variables
    config = Config()
    assert config.model_config["env_prefix"] == "HADES_"
    assert config.model_config["env_nested_delimiter"] == "__" 