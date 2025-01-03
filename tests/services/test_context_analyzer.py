"""Tests for context analyzer service."""

import pytest
from unittest.mock import MagicMock, patch

from hades.core.models import (
    ContextMetadata,
    AllocationDecision,
    ElysiumRealm,
    AsphodelRealm,
    TartarusRealm
)
from hades.core.exceptions import MCPError
from hades.services.context_analyzer import ContextAnalyzer

@pytest.fixture
def elysium():
    """Create mock elysium realm."""
    mock = MagicMock(spec=ElysiumRealm)
    mock.capacity = 1000
    return mock

@pytest.fixture
def asphodel():
    """Create mock asphodel realm."""
    mock = MagicMock(spec=AsphodelRealm)
    mock.window_size = 2000
    return mock

@pytest.fixture
def tartarus():
    """Create mock tartarus realm."""
    mock = MagicMock(spec=TartarusRealm)
    mock.archive = {}
    return mock

@pytest.fixture
def context_analyzer(elysium, asphodel, tartarus):
    """Create context analyzer instance."""
    return ContextAnalyzer({
        "elysium_capacity": elysium.capacity,
        "asphodel_window": asphodel.window_size,
        "lethe_threshold": 0.5
    })

@pytest.mark.asyncio
async def test_analyze_context(context_analyzer):
    """Test context analysis."""
    context = "This is a test context"
    metadata = await context_analyzer.analyze(context)

    assert isinstance(metadata, ContextMetadata)
    assert metadata.tokens == ["This", "is", "a", "test", "context"]
    assert "relevance" in metadata.semantics
    assert len(metadata.relationships) > 0

@pytest.mark.asyncio
async def test_allocate_critical_context(context_analyzer):
    """Test allocation decision for critical context."""
    context = ContextMetadata(
        tokens=["test"],
        semantics={"relevance": 1.0},
        relationships=[]
    )

    decision = await context_analyzer.allocate(context)

    assert isinstance(decision, AllocationDecision)
    assert decision.realm == "elysium"
    assert decision.priority == "high"

@pytest.mark.asyncio
async def test_allocate_active_context(context_analyzer):
    """Test allocation decision for active context."""
    context = ContextMetadata(
        tokens=["test"] * 2000,  # Too large for Elysium
        semantics={"relevance": 1.0},
        relationships=[]
    )

    decision = await context_analyzer.allocate(context)

    assert isinstance(decision, AllocationDecision)
    assert decision.realm == "asphodel"
    assert decision.priority == "medium"

@pytest.mark.asyncio
async def test_allocate_archived_context(context_analyzer):
    """Test allocation decision for archived context."""
    context = ContextMetadata(
        tokens=["test"] * 2000,  # Too large for Elysium
        semantics={"relevance": 0.0},  # Low relevance
        relationships=[]
    )

    decision = await context_analyzer.allocate(context)

    assert isinstance(decision, AllocationDecision)
    assert decision.realm == "tartarus"
    assert decision.priority == "low"

@pytest.mark.asyncio
async def test_tokenize_empty_context(context_analyzer):
    """Test tokenization of empty context."""
    tokens = context_analyzer._tokenize("")
    assert tokens == []

@pytest.mark.asyncio
async def test_extract_semantics(context_analyzer):
    """Test semantic extraction."""
    tokens = ["test", "context"]
    semantics = await context_analyzer._extract_semantics(tokens)
    
    assert isinstance(semantics, dict)
    assert "relevance" in semantics
    assert isinstance(semantics["relevance"], float)

@pytest.mark.asyncio
async def test_identify_relationships(context_analyzer):
    """Test relationship identification."""
    context = "This is a test"
    relationships = await context_analyzer._identify_relationships(context)
    
    assert isinstance(relationships, list)
    assert len(relationships) > 0
    for rel in relationships:
        assert isinstance(rel, dict)
        assert "type" in rel
        assert "source" in rel
        assert "target" in rel
        assert "weight" in rel 

@pytest.mark.asyncio
async def test_analyze_error_handling(context_analyzer):
    """Test error handling in analyze method."""
    with patch.object(context_analyzer, '_tokenize', side_effect=Exception("Tokenization failed")):
        with pytest.raises(MCPError) as exc_info:
            await context_analyzer.analyze("test context")
        
        assert exc_info.value.code == "ANALYSIS_ERROR"
        assert "Tokenization failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_allocate_error_handling(context_analyzer):
    """Test error handling in allocate method."""
    context = ContextMetadata(
        tokens=["test"],
        semantics={"relevance": 1.0},
        relationships=[]
    )
    
    with patch.object(context_analyzer, '_is_critical', side_effect=Exception("Allocation failed")):
        with pytest.raises(MCPError) as exc_info:
            await context_analyzer.allocate(context)
        
        assert exc_info.value.code == "ALLOCATION_ERROR"
        assert "Allocation failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_extract_semantics_long_context(context_analyzer):
    """Test semantic extraction with long context."""
    long_context = "test " * 50  # More than 100 characters
    semantics = await context_analyzer._extract_semantics(long_context)
    
    assert semantics["relevance"] == 0.8

@pytest.mark.asyncio
async def test_extract_semantics_short_context(context_analyzer):
    """Test semantic extraction with short context."""
    short_context = "test"  # Less than 100 characters
    semantics = await context_analyzer._extract_semantics(short_context)
    
    assert semantics["relevance"] == 0.3

@pytest.mark.asyncio
async def test_identify_relationships_single_word(context_analyzer):
    """Test relationship identification with single word."""
    context = "test"
    relationships = await context_analyzer._identify_relationships(context)
    
    assert len(relationships) == 0

@pytest.mark.asyncio
async def test_identify_relationships_multiple_words(context_analyzer):
    """Test relationship identification with multiple words."""
    context = "This is a test"
    relationships = await context_analyzer._identify_relationships(context)
    
    assert len(relationships) == 3  # "This-is", "is-a", "a-test"
    for i, rel in enumerate(relationships):
        words = context.split()
        assert rel["type"] == "sequence"
        assert rel["source"] == words[i]
        assert rel["target"] == words[i + 1]
        assert rel["weight"] == "1.0"

@pytest.mark.asyncio
async def test_is_critical_edge_cases(context_analyzer):
    """Test edge cases for critical context determination."""
    # Test with missing relevance
    metadata = ContextMetadata(
        tokens=["test"],
        semantics={},  # No relevance
        relationships=[]
    )
    assert not context_analyzer._is_critical(metadata)
    
    # Test with exactly elysium capacity
    metadata = ContextMetadata(
        tokens=["test"] * context_analyzer.elysium_capacity,
        semantics={"relevance": 1.0},
        relationships=[]
    )
    assert context_analyzer._is_critical(metadata)
    
    # Test with exactly lethe threshold
    metadata = ContextMetadata(
        tokens=["test"],
        semantics={"relevance": context_analyzer.lethe_threshold},
        relationships=[]
    )
    assert not context_analyzer._is_critical(metadata)

@pytest.mark.asyncio
async def test_is_active_edge_cases(context_analyzer):
    """Test edge cases for active context determination."""
    # Test with missing relevance
    metadata = ContextMetadata(
        tokens=["test"],
        semantics={},  # No relevance
        relationships=[]
    )
    assert not context_analyzer._is_active(metadata)
    
    # Test with exactly asphodel window
    metadata = ContextMetadata(
        tokens=["test"] * context_analyzer.asphodel_window,
        semantics={"relevance": 1.0},
        relationships=[]
    )
    assert context_analyzer._is_active(metadata)
    
    # Test with exactly relevance threshold
    metadata = ContextMetadata(
        tokens=["test"],
        semantics={"relevance": 0.3},
        relationships=[]
    )
    assert not context_analyzer._is_active(metadata) 