"""Tests for memory allocator service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from hades.core.models import (
    ContextMetadata,
    AllocationDecision,
    ElysiumRealm,
    AsphodelRealm,
    TartarusRealm,
    StyxController,
    LetheManager
)
from hades.core.exceptions import MCPError
from hades.services.memory_allocator import MemoryAllocator

@pytest.fixture
def mock_elysium():
    """Create mock elysium realm."""
    mock = MagicMock(spec=ElysiumRealm)
    mock.capacity = 1000
    preserved_context = PropertyMock(return_value={})
    type(mock).preserved_context = preserved_context
    mock._preserved_context = preserved_context
    return mock

@pytest.fixture
def mock_asphodel():
    """Create mock asphodel realm."""
    mock = MagicMock(spec=AsphodelRealm)
    mock.window_size = 2000
    active_context = PropertyMock(return_value={})
    type(mock).active_context = active_context
    mock._active_context = active_context
    return mock

@pytest.fixture
def mock_tartarus():
    """Create mock tartarus realm."""
    mock = MagicMock(spec=TartarusRealm)
    archive = PropertyMock(return_value={})
    type(mock).archive = archive
    mock._archive = archive
    return mock

@pytest.fixture
def styx_controller(mock_elysium, mock_asphodel, mock_tartarus):
    """Create mock styx controller."""
    controller = MagicMock(spec=StyxController)
    controller.manage_flow = AsyncMock()
    controller.elysium = mock_elysium
    controller.asphodel = mock_asphodel
    controller.tartarus = mock_tartarus
    return controller

@pytest.fixture
def lethe_manager():
    """Create mock lethe manager."""
    manager = MagicMock(spec=LetheManager)
    manager.forget = AsyncMock()
    return manager

@pytest.fixture
def memory_allocator(mock_elysium, mock_asphodel, mock_tartarus, styx_controller, lethe_manager):
    """Create memory allocator instance."""
    allocator = MemoryAllocator(
        elysium_capacity=1000,
        asphodel_window=2000,
        lethe_threshold=0.5
    )
    allocator.elysium = mock_elysium
    allocator.asphodel = mock_asphodel
    allocator.tartarus = mock_tartarus
    allocator.styx = styx_controller
    allocator.lethe = lethe_manager
    return allocator

@pytest.mark.asyncio
async def test_memory_allocator_initialization(memory_allocator):
    """Test memory allocator initialization."""
    assert isinstance(memory_allocator.elysium, ElysiumRealm)
    assert isinstance(memory_allocator.asphodel, AsphodelRealm)
    assert isinstance(memory_allocator.tartarus, TartarusRealm)
    assert memory_allocator.elysium.capacity == 1000
    assert memory_allocator.asphodel.window_size == 2000

@pytest.mark.asyncio
async def test_allocate_critical_context(memory_allocator):
    """Test allocation of critical context."""
    context = "test context"
    metadata = ContextMetadata(
        tokens=["test", "context"],
        semantics={"relevance": 1.0},
        relationships=[]
    )

    decision = await memory_allocator.allocate(context, metadata)

    assert isinstance(decision, AllocationDecision)
    assert decision.realm == "elysium"
    assert decision.priority == "high"
    memory_allocator.styx.manage_flow.assert_called_once_with(context, metadata)

@pytest.mark.asyncio
async def test_allocate_active_context(memory_allocator):
    """Test allocation of active context."""
    context = "test context"
    metadata = ContextMetadata(
        tokens=["test"] * 2000,  # Too large for Elysium
        semantics={"relevance": 0.8},
        relationships=[]
    )

    decision = await memory_allocator.allocate(context, metadata)

    assert isinstance(decision, AllocationDecision)
    assert decision.realm == "asphodel"
    assert decision.priority == "medium"
    memory_allocator.styx.manage_flow.assert_called_once_with(context, metadata)

@pytest.mark.asyncio
async def test_allocate_archived_context(memory_allocator):
    """Test allocation of archived context."""
    context = "test context"
    metadata = ContextMetadata(
        tokens=["test"] * 2000,  # Too large for Elysium
        semantics={"relevance": 0.3},  # Below active threshold
        relationships=[]
    )

    decision = await memory_allocator.allocate(context, metadata)

    assert isinstance(decision, AllocationDecision)
    assert decision.realm == "tartarus"
    assert decision.priority == "low"
    memory_allocator.styx.manage_flow.assert_called_once_with(context, metadata)

@pytest.mark.asyncio
async def test_cleanup_old_contexts(memory_allocator):
    """Test cleanup of old contexts."""
    # Add some contexts to Tartarus
    context_ids = ["1", "2", "3"]
    test_archive = {
        context_id: {
            "tokens": ["test"],
            "semantics": {"relevance": 0.1},
            "relationships": []
        }
        for context_id in context_ids
    }
    memory_allocator.tartarus._archive.return_value = test_archive
    
    await memory_allocator._cleanup_old_contexts()
    
    # Verify Lethe manager was called for each context
    assert memory_allocator.lethe.forget.call_count == len(context_ids)
    for context_id in context_ids:
        memory_allocator.lethe.forget.assert_any_call(context_id, memory_allocator.tartarus)

@pytest.mark.asyncio
async def test_get_context_stats(memory_allocator):
    """Test getting context statistics."""
    # Set up test data
    memory_allocator.elysium._preserved_context.return_value = ["test"] * 5
    memory_allocator.asphodel._active_context.return_value = ["test"] * 10
    memory_allocator.tartarus._archive.return_value = {"1": {}, "2": {}, "3": {}}
    
    stats = await memory_allocator.get_context_stats()
    
    assert stats["elysium_used"] == 5
    assert stats["elysium_capacity"] == 1000
    assert stats["asphodel_used"] == 10
    assert stats["asphodel_capacity"] == 2000
    assert stats["tartarus_archived"] == 3

@pytest.mark.asyncio
async def test_cleanup_error_handling(memory_allocator):
    """Test error handling during cleanup."""
    # Add some test data to Tartarus
    test_archive = {"1": {}, "2": {}}
    memory_allocator.tartarus._archive.return_value = test_archive
    memory_allocator.lethe.forget.side_effect = Exception("Cleanup failed")
    
    with pytest.raises(MCPError) as exc_info:
        await memory_allocator.cleanup()
    
    assert exc_info.value.code == "CLEANUP_ERROR"
    assert "Cleanup failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_context_stats_error_handling(memory_allocator):
    """Test error handling in get_context_stats."""
    # Make preserved_context raise an exception
    type(memory_allocator.elysium).preserved_context = PropertyMock(side_effect=Exception("Stats failed"))

    with pytest.raises(MCPError) as exc_info:
        await memory_allocator.get_context_stats()
    
    assert exc_info.value.code == "STATS_ERROR"
    assert "Stats failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_handle_elysium_allocation(memory_allocator):
    """Test handling allocation to Elysium realm."""
    context = "test context"
    metadata = ContextMetadata(
        tokens=["test"],
        semantics={"relevance": 0.9},
        relationships=[],
        id="test_id"
    )

    await memory_allocator._handle_elysium_allocation(context, metadata)
    
    memory_allocator.elysium.__setitem__.assert_called_once_with(
        metadata.id,
        {
            "context": context,
            "metadata": metadata
        }
    )

@pytest.mark.asyncio
async def test_handle_asphodel_allocation(memory_allocator):
    """Test handling allocation to Asphodel realm."""
    context = "test context"
    metadata = ContextMetadata(
        tokens=["test"],
        semantics={"relevance": 0.6},
        relationships=[],
        id="test_id"
    )

    await memory_allocator._handle_asphodel_allocation(context, metadata)
    
    memory_allocator.asphodel.__setitem__.assert_called_once_with(
        metadata.id,
        {
            "context": context,
            "metadata": metadata
        }
    )

@pytest.mark.asyncio
async def test_handle_tartarus_allocation(memory_allocator):
    """Test handling allocation to Tartarus realm."""
    context = "test context"
    metadata = ContextMetadata(
        tokens=["test"],
        semantics={"relevance": 0.3},
        relationships=[],
        id="test_id"
    )

    await memory_allocator._handle_tartarus_allocation(context, metadata)
    
    memory_allocator.tartarus.__setitem__.assert_called_once_with(
        metadata.id,
        {
            "context": context,
            "metadata": metadata
        }
    ) 