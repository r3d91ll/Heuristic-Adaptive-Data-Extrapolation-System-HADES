"""Base service class."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from hades.core.exceptions import MCPError

class BaseService(ABC):
    """Base class for all services."""

    def __init__(self):
        """Initialize base service."""
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    def _validate_initialized(self) -> None:
        """Validate that the service is initialized."""
        if not self.is_initialized:
            raise MCPError(
                "SERVICE_NOT_INITIALIZED",
                "Service must be initialized before use"
            )

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize service."""
        pass  # pragma: no cover

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown service."""
        pass  # pragma: no cover

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        pass  # pragma: no cover 