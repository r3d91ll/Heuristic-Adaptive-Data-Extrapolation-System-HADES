"""Configuration classes for HADES."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

class DatabaseConfig(BaseModel):
    """Database configuration."""
    host: str = Field(default="localhost")
    port: int = Field(default=8529)
    username: str = Field(default="root")
    password: str = Field(default="")
    database: str = Field(default="hades")

    @field_validator("host")
    def validate_host(cls, v: str) -> str:
        """Validate host is not empty."""
        if not v:
            raise ValueError("Host cannot be empty")
        return v

    @field_validator("port")
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not 0 < v < 65536:
            raise ValueError("Port must be between 1 and 65535")
        return v


class MilvusConfig(BaseModel):
    """Milvus configuration."""

    host: str = Field(default="localhost")
    port: int = Field(default=19530)
    user: str = Field(default="root")
    password: str = Field(default="")
    collection: str = Field(default="vectors")

    @field_validator("host")
    def validate_host(cls, v: str) -> str:
        """Validate host is not empty."""
        if not v:
            raise ValueError("Host cannot be empty")
        return v

    @field_validator("port")
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not 0 < v < 65536:
            raise ValueError("Port must be between 1 and 65535")
        return v


class HybridSearchConfig(BaseModel):
    """Hybrid search configuration."""

    collection: str = Field(default="documents")
    vector_field: str = Field(default="vector")
    text_field: str = Field(default="text")
    id_field: str = Field(default="_id")
    min_score: float = Field(default=0.0)
    max_results: int = Field(default=10)

    @field_validator("collection")
    def validate_collection(cls, v: str) -> str:
        """Validate collection name is not empty."""
        if not v:
            raise ValueError("Collection name cannot be empty")
        return v

    @field_validator("vector_field")
    def validate_vector_field(cls, v: str) -> str:
        """Validate vector field name is not empty."""
        if not v:
            raise ValueError("Vector field name cannot be empty")
        return v

    @field_validator("text_field")
    def validate_text_field(cls, v: str) -> str:
        """Validate text field name is not empty."""
        if not v:
            raise ValueError("Text field name cannot be empty")
        return v

    @field_validator("id_field")
    def validate_id_field(cls, v: str) -> str:
        """Validate ID field name is not empty."""
        if not v:
            raise ValueError("ID field name cannot be empty")
        return v

    @field_validator("min_score")
    def validate_min_score(cls, v: float) -> float:
        """Validate minimum score is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Minimum score must be between 0 and 1")
        return v

    @field_validator("max_results")
    def validate_max_results(cls, v: int) -> int:
        """Validate maximum results is positive."""
        if v <= 0:
            raise ValueError("Maximum results must be positive")
        return v


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(default="localhost")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    thread_pool_size: int = Field(default=4)

    @field_validator("host")
    def validate_host(cls, v: str) -> str:
        """Validate host is not empty."""
        if not v:
            raise ValueError("Host cannot be empty")
        return v

    @field_validator("port")
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not 0 < v < 65536:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("thread_pool_size")
    def validate_thread_pool_size(cls, v: int) -> int:
        """Validate thread pool size is positive."""
        if v <= 0:
            raise ValueError("Thread pool size must be positive")
        return v


class MemoryConfig(BaseModel):
    """Memory management configuration."""
    elysium_capacity: int = Field(
        default=1000,
        description="Maximum number of tokens to preserve in Elysium (n_keep)"
    )
    asphodel_window: int = Field(
        default=2000,
        description="Size of active context window in Asphodel"
    )
    lethe_threshold: float = Field(
        default=0.5,
        description="Relevance threshold for forgetting in Lethe"
    )
    enable_archival: bool = Field(
        default=True,
        description="Enable archival storage in Tartarus"
    )


class Config(BaseSettings):
    """Main configuration."""

    memory: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="Memory management configuration"
    )
    hybrid_search: HybridSearchConfig = Field(
        default_factory=HybridSearchConfig,
        description="Hybrid search configuration"
    )

    model_config = {
        "env_prefix": "HADES_",
        "env_nested_delimiter": "__"
    } 