"""Tests for the base service."""

import pytest
from typing import Dict, Any

from hades.core.exceptions import MCPError
from hades.services.base import BaseService

class ConcreteService(BaseService):
    """Concrete implementation of BaseService for testing."""
    
    async def initialize(self) -> None:
        """Initialize service."""
        self._initialized = True
    
    async def shutdown(self) -> None:
        """Shutdown service."""
        self._initialized = False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        return {"status": "ok" if self.is_initialized else "error"}

class EmptyService(BaseService):
    """Empty service implementation that just passes."""
    
    async def initialize(self) -> None:
        """Initialize service."""
        pass
    
    async def shutdown(self) -> None:
        """Shutdown service."""
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        pass

@pytest.fixture
def service():
    """Create a concrete service instance for testing."""
    return ConcreteService()

def test_service_initialization(service):
    """Test service initialization state."""
    assert not service.is_initialized
    assert not service._initialized

@pytest.mark.asyncio
async def test_initialize(service):
    """Test service initialization."""
    await service.initialize()
    assert service.is_initialized
    assert service._initialized

@pytest.mark.asyncio
async def test_shutdown(service):
    """Test service shutdown."""
    await service.initialize()
    assert service.is_initialized
    
    await service.shutdown()
    assert not service.is_initialized
    assert not service._initialized

@pytest.mark.asyncio
async def test_health_check_initialized(service):
    """Test health check when service is initialized."""
    await service.initialize()
    health = await service.health_check()
    assert health["status"] == "ok"

@pytest.mark.asyncio
async def test_health_check_not_initialized(service):
    """Test health check when service is not initialized."""
    health = await service.health_check()
    assert health["status"] == "error"

def test_validate_initialized_success(service):
    """Test validation when service is initialized."""
    service._initialized = True
    service._validate_initialized()  # Should not raise

def test_validate_initialized_failure(service):
    """Test validation when service is not initialized."""
    with pytest.raises(MCPError) as exc_info:
        service._validate_initialized()
    assert exc_info.value.code == "SERVICE_NOT_INITIALIZED"
    assert "Service must be initialized before use" in str(exc_info.value)

def test_is_initialized_property(service):
    """Test is_initialized property."""
    assert not service.is_initialized
    service._initialized = True
    assert service.is_initialized 

@pytest.mark.asyncio
async def test_empty_service_abstract_methods():
    """Test empty service implementation with pass statements."""
    service = EmptyService()
    
    # Test initialize
    await service.initialize()  # This will execute the pass statement
    assert not service.is_initialized  # Should still be False since we just pass
    
    # Test shutdown
    await service.shutdown()  # This will execute the pass statement
    assert not service.is_initialized
    
    # Test health check
    result = await service.health_check()  # This will execute the pass statement
    assert result is None  # Should return None since we just pass

    # Test that we can subclass BaseService
    assert isinstance(service, BaseService)
    # Test that we've implemented all abstract methods
    assert hasattr(service, 'initialize')
    assert hasattr(service, 'shutdown')
    assert hasattr(service, 'health_check') 