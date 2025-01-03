"""Tests for data models."""

import pytest
from typing import Dict, Any, List
import uuid
from pydantic import ValidationError
from unittest.mock import patch

from hades.core.models import (
    QueryArgs, VectorSearchArgs, HybridSearchArgs, CallToolRequest,
    ListToolsRequest, ContextMetadata, AllocationDecision, ElysiumRealm,
    AsphodelRealm, TartarusRealm, StyxController, LetheManager
)

def test_query_args_valid():
    """Test valid query arguments."""
    args = QueryArgs(query="FOR doc IN collection RETURN doc")
    assert args.query == "FOR doc IN collection RETURN doc"
    assert args.bind_vars is None

    args_with_vars = QueryArgs(
        query="FOR doc IN collection FILTER doc.name == @name RETURN doc",
        bind_vars={"name": "test"}
    )
    assert args_with_vars.bind_vars == {"name": "test"}

def test_query_args_validation():
    """Test query arguments validation."""
    with pytest.raises(ValidationError) as exc_info:
        QueryArgs(query="")
    assert "Query cannot be empty" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        QueryArgs(query="   ")
    assert "Query cannot be empty" in str(exc_info.value)

def test_vector_search_args_valid():
    """Test valid vector search arguments."""
    args = VectorSearchArgs(
        collection="test_collection",
        vector=[0.1, 0.2, 0.3],
        top_k=5
    )
    assert args.collection == "test_collection"
    assert args.vector == [0.1, 0.2, 0.3]
    assert args.top_k == 5

def test_vector_search_args_validation():
    """Test vector search arguments validation."""
    with pytest.raises(ValidationError) as exc_info:
        VectorSearchArgs(collection="test", vector=[], top_k=5)
    assert "Vector cannot be empty" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        VectorSearchArgs(collection="test", vector=[0.1], top_k=0)
    assert "top_k must be positive" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        VectorSearchArgs(collection="test", vector=[0.1], top_k=-1)
    assert "top_k must be positive" in str(exc_info.value)

def test_hybrid_search_args_valid():
    """Test valid hybrid search arguments."""
    args = HybridSearchArgs(
        collection="test_collection",
        vector=[0.1, 0.2, 0.3],
        filter_query="doc.type == @type",
        bind_vars={"type": "test"},
        top_k=5
    )
    assert args.collection == "test_collection"
    assert args.vector == [0.1, 0.2, 0.3]
    assert args.filter_query == "doc.type == @type"
    assert args.bind_vars == {"type": "test"}
    assert args.top_k == 5

def test_hybrid_search_args_validation():
    """Test hybrid search arguments validation."""
    with pytest.raises(ValidationError) as exc_info:
        HybridSearchArgs(
            collection="test",
            vector=[],
            filter_query="doc.type == @type"
        )
    assert "Vector cannot be empty" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        HybridSearchArgs(
            collection="test",
            vector=[0.1],
            filter_query="doc.type == @type",
            top_k=0
        )
    assert "top_k must be positive" in str(exc_info.value)

def test_call_tool_request_valid():
    """Test valid call tool request."""
    request = CallToolRequest(tool_name="test_tool", args={"param": "value"})
    assert request.tool_name == "test_tool"
    assert request.args == {"param": "value"}

    # Test default empty args
    request = CallToolRequest(tool_name="test_tool")
    assert request.args == {}

def test_call_tool_request_validation():
    """Test call tool request validation."""
    with pytest.raises(ValidationError) as exc_info:
        CallToolRequest(tool_name="")
    assert "Tool name cannot be empty" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        CallToolRequest(tool_name="   ")
    assert "Tool name cannot be empty" in str(exc_info.value)

def test_list_tools_request_valid():
    """Test list tools request."""
    request = ListToolsRequest()
    assert isinstance(request, ListToolsRequest)

def test_context_metadata_valid():
    """Test valid context metadata."""
    metadata = ContextMetadata(
        tokens=["test", "tokens"],
        semantics={"test": 0.5},
        relationships=[{"type": "test", "target": "other"}]
    )
    assert isinstance(metadata.id, str)
    assert len(metadata.id) > 0
    assert metadata.tokens == ["test", "tokens"]
    assert metadata.semantics == {"test": 0.5}
    assert metadata.relationships == [{"type": "test", "target": "other"}]

def test_allocation_decision_valid():
    """Test valid allocation decision."""
    decision = AllocationDecision(realm="elysium", priority="high")
    assert decision.realm == "elysium"
    assert decision.priority == "high"

@pytest.mark.asyncio
async def test_elysium_realm():
    """Test Elysium realm functionality."""
    realm = ElysiumRealm(capacity=5)
    assert realm.capacity == 5
    assert realm.preserved_context == {}

    # Test __setitem__
    realm["test"] = {"data": "value"}
    assert realm.preserved_context["test"] == {"data": "value"}

    # Test preserve
    success = await realm.preserve("short context")
    assert success
    assert len(realm.preserved_context) == 2  # Including the one from __setitem__

    # Test preserve with too long context
    success = await realm.preserve("this is a very long context that exceeds capacity")
    assert not success

@pytest.mark.asyncio
async def test_asphodel_realm():
    """Test Asphodel realm functionality."""
    realm = AsphodelRealm(window_size=2)
    assert realm.window_size == 2
    assert realm.active_context == {}
    assert realm.computation_cache == {}

    # Test __setitem__
    realm["test"] = {"data": "value"}
    assert realm.active_context["test"] == {"data": "value"}

    # Test process
    await realm.process("message 1")
    await realm.process("message 2")
    assert len(realm.active_context) == 2

    # Test window size enforcement
    await realm.process("message 3")
    assert len(realm.active_context) == 2

@pytest.mark.asyncio
async def test_tartarus_realm():
    """Test Tartarus realm functionality."""
    realm = TartarusRealm()
    assert realm.archive == {}
    assert realm.relationship_graph == {}

    # Test __setitem__
    realm["test"] = {"data": "value"}
    assert realm.archive["test"] == {"data": "value"}

    # Test archive_context
    metadata = ContextMetadata(
        tokens=["test"],
        semantics={"test": 0.5},
        relationships=[]
    )
    context_id = await realm.archive_context(metadata)
    assert isinstance(context_id, str)
    assert context_id in realm.archive

@pytest.mark.asyncio
async def test_styx_controller():
    """Test Styx controller functionality."""
    controller = StyxController(
        elysium=ElysiumRealm(capacity=5),
        asphodel=AsphodelRealm(window_size=2),
        tartarus=TartarusRealm()
    )

    metadata = ContextMetadata(
        tokens=["test"],
        semantics={"test": 0.5},
        relationships=[]
    )

    # Test manage_flow with short context (should preserve)
    await controller.manage_flow("short", metadata)
    assert len(controller.elysium.preserved_context) == 1
    assert any("short" in str(v.get("tokens")) for v in controller.elysium.preserved_context.values())

    # Test manage_flow with long context (should process in asphodel)
    long_context = "this is a longer context that should definitely go to asphodel"
    await controller.manage_flow(long_context, metadata)
    assert len(controller.asphodel.active_context) == 1
    assert any(long_context == v.get("message") for v in controller.asphodel.active_context.values())

    # Test manage_flow with another long context (should maintain window size)
    another_context = "another long context for testing window size"
    await controller.manage_flow(another_context, metadata)
    assert len(controller.asphodel.active_context) == 2
    assert any(another_context == v.get("message") for v in controller.asphodel.active_context.values())

    # Test overflow of window size
    overflow_context = "this should cause overflow"
    await controller.manage_flow(overflow_context, metadata)
    assert len(controller.asphodel.active_context) == 2
    assert any(overflow_context == v.get("message") for v in controller.asphodel.active_context.values())

    # Mock _is_active to return False to test tartarus archival
    controller._is_active = lambda _: False
    archive_context = "this should go to tartarus"
    await controller.manage_flow(archive_context, metadata)
    assert any(metadata.model_dump() == v for v in controller.tartarus.archive.values())

@pytest.mark.asyncio
async def test_lethe_manager():
    """Test Lethe manager functionality."""
    manager = LetheManager(threshold=0.5)
    tartarus = TartarusRealm()
    
    # Add some test data
    context_id = "test_id"
    tartarus.archive[context_id] = {"data": "value"}
    
    # Test forget
    await manager.forget(context_id, tartarus)
    
    # Test _assess_relevance directly
    relevance = await manager._assess_relevance(context_id, tartarus)
    assert 0 <= relevance <= 1  # Should return a float between 0 and 1

    # Test with non-existent context
    await manager.forget("non_existent", tartarus)  # Should not raise

@pytest.mark.asyncio
async def test_lethe_manager_forget_below_threshold():
    """Test LetheManager forget when relevance is below threshold."""
    manager = LetheManager(threshold=0.7)  # High threshold to ensure forgetting
    tartarus = TartarusRealm()
    context_id = "test_context"
    tartarus.archive[context_id] = {"data": "test"}
    
    # Mock _assess_relevance to return a low value
    with patch.object(manager, '_assess_relevance', return_value=0.5):
        await manager.forget(context_id, tartarus)
        assert context_id not in tartarus.archive

def test_model_field_defaults():
    """Test model field defaults."""
    # Test QueryArgs defaults
    args = QueryArgs(query="test")
    assert args.bind_vars is None

    # Test VectorSearchArgs defaults
    args = VectorSearchArgs(collection="test", vector=[0.1])
    assert args.top_k == 10

    # Test HybridSearchArgs defaults
    args = HybridSearchArgs(collection="test", vector=[0.1], filter_query="test")
    assert args.top_k == 10
    assert args.bind_vars is None

    # Test CallToolRequest defaults
    request = CallToolRequest(tool_name="test")
    assert request.args == {} 

def test_styx_controller_is_active():
    """Test StyxController._is_active method."""
    controller = StyxController(
        elysium=ElysiumRealm(capacity=5),
        asphodel=AsphodelRealm(window_size=2),
        tartarus=TartarusRealm()
    )
    assert controller._is_active("any context") is True  # Currently always returns True 