"""Tests for the request handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from hades.core.exceptions import MCPError
from hades.core.models import (
    QueryArgs,
    VectorSearchArgs,
    HybridSearchArgs,
    CallToolRequest,
    ListToolsRequest
)
from hades.server.handlers import RequestHandler, mcp_tool
from hades.services.database import DatabaseService
from hades.services.vector import VectorService
from hades.services.hybrid import HybridSearchService

@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    return {
        "db_service": AsyncMock(spec=DatabaseService),
        "vector_service": AsyncMock(spec=VectorService),
        "hybrid_service": AsyncMock(spec=HybridSearchService)
    }

@pytest.fixture
def request_handler(mock_services):
    """Create a request handler instance for testing."""
    return RequestHandler(mock_services)

def test_mcp_tool_decorator():
    """Test the mcp_tool decorator."""
    @mcp_tool("Test description")
    async def test_tool():
        return "success"
    
    assert hasattr(test_tool, "is_tool")
    assert test_tool.description == "Test description"

@pytest.mark.asyncio
async def test_mcp_tool_decorator_error_handling():
    """Test error handling in the mcp_tool decorator."""
    @mcp_tool("Test description")
    async def failing_tool():
        raise Exception("Tool failed")
    
    with pytest.raises(MCPError) as exc_info:
        await failing_tool()
    
    assert exc_info.value.code == "TOOL_ERROR"
    assert "Tool failed" in str(exc_info.value)

def test_request_handler_initialization(request_handler):
    """Test request handler initialization."""
    assert request_handler.db_service is not None
    assert request_handler.vector_service is not None
    assert request_handler.hybrid_service is not None
    assert isinstance(request_handler.tools, dict)

def test_request_handler_tool_registration(request_handler):
    """Test tool registration."""
    tools = request_handler.tools
    assert "execute_query" in tools
    assert "vector_search" in tools
    assert "hybrid_search" in tools
    
    for tool_info in tools.values():
        assert "handler" in tool_info
        assert "description" in tool_info
        assert "schema" in tool_info

@pytest.mark.asyncio
async def test_handle_list_tools_request(request_handler):
    """Test handling list tools request."""
    request = ListToolsRequest(method="tools/list")
    response = await request_handler.handle_request(request)
    
    assert response["success"] is True
    assert "tools" in response
    assert isinstance(response["tools"], list)
    assert len(response["tools"]) > 0
    
    for tool in response["tools"]:
        assert "name" in tool
        assert "description" in tool
        assert "schema" in tool

@pytest.mark.asyncio
async def test_handle_invalid_request(request_handler):
    """Test handling invalid request type."""
    invalid_request = MagicMock()  # Not a valid request type
    response = await request_handler.handle_request(invalid_request)
    
    assert response["success"] is False
    assert response["error"]["code"] == "INVALID_REQUEST"

@pytest.mark.asyncio
async def test_handle_tool_call_success(request_handler, mock_services):
    """Test successful tool call."""
    mock_services["db_service"].execute_query.return_value = [{"result": "success"}]
    
    request = CallToolRequest(
        tool_name="execute_query",
        args={
            "query": "FOR doc IN collection RETURN doc"
        }
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is True
    assert response["result"] == [{"result": "success"}]

@pytest.mark.asyncio
async def test_handle_tool_call_unknown_tool(request_handler):
    """Test calling unknown tool."""
    request = CallToolRequest(
        tool_name="unknown_tool",
        args={}
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is False
    assert response["error"]["code"] == "INVALID_TOOL"

@pytest.mark.asyncio
async def test_execute_query_tool(request_handler, mock_services):
    """Test execute query tool."""
    expected_result = [{"data": "test"}]
    mock_services["db_service"].execute_query.return_value = expected_result
    
    result = await request_handler.execute_query(
        query="FOR doc IN collection RETURN doc"
    )
    
    assert result == expected_result
    mock_services["db_service"].execute_query.assert_called_once()

@pytest.mark.asyncio
async def test_vector_search_tool(request_handler, mock_services):
    """Test vector search tool."""
    expected_result = [{"vector_id": 1, "score": 0.9}]
    mock_services["vector_service"].search.return_value = expected_result
    
    result = await request_handler.vector_search(
        collection="test_collection",
        vector=[0.1, 0.2, 0.3]
    )
    
    assert result == expected_result
    mock_services["vector_service"].search.assert_called_once()

@pytest.mark.asyncio
async def test_hybrid_search_tool(request_handler, mock_services):
    """Test hybrid search tool."""
    expected_result = [{"id": 1, "score": 0.9, "text": "test"}]
    mock_services["hybrid_service"].search.return_value = expected_result
    
    result = await request_handler.hybrid_search(
        collection="test_collection",
        vector=[0.1, 0.2, 0.3],
        filter_query="doc.type == 'test'"
    )
    
    assert result == expected_result
    mock_services["hybrid_service"].search.assert_called_once()

@pytest.mark.asyncio
async def test_tool_validation_error(request_handler):
    """Test tool argument validation error."""
    with pytest.raises(MCPError) as exc_info:
        await request_handler.vector_search(
            collection="test_collection",
            vector=[]  # Invalid empty vector
        )
    
    assert "validation" in str(exc_info.value).lower()

@pytest.mark.asyncio
async def test_handle_internal_error(request_handler, mock_services):
    """Test handling internal error in request handler."""
    mock_services["db_service"].execute_query.side_effect = Exception("Internal error")
    
    request = CallToolRequest(
        tool_name="execute_query",
        args={
            "query": "FOR doc IN collection RETURN doc"
        }
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is False
    assert response["error"]["code"] == "INTERNAL_ERROR" 

@pytest.mark.asyncio
async def test_handle_validation_error(request_handler, mock_services):
    """Test handling validation error in request handler."""
    mock_services["vector_service"].search.side_effect = MCPError(
        "VALIDATION_ERROR",
        "Validation failed",
        {"param": "vector"}
    )
    
    request = CallToolRequest(
        tool_name="vector_search",
        args={
            "collection": "test_collection",
            "vector": [0.1, 0.2, 0.3]
        }
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is False
    assert response["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in response["error"]

@pytest.mark.asyncio
async def test_vector_search_invalid_top_k(request_handler):
    """Test vector search with invalid top_k parameter."""
    with pytest.raises(MCPError) as exc_info:
        await request_handler.vector_search(
            collection="test_collection",
            vector=[0.1, 0.2, 0.3],
            top_k=0  # Invalid top_k
        )
    
    assert exc_info.value.code == "VALIDATION_ERROR"
    assert "top_k must be positive" in str(exc_info.value)
    assert exc_info.value.details["param"] == "top_k"

@pytest.mark.asyncio
async def test_hybrid_search_validation(request_handler):
    """Test hybrid search validation."""
    # Test with empty vector
    with pytest.raises(MCPError) as exc_info:
        await request_handler.hybrid_search(
            collection="test_collection",
            vector=[],
            filter_query="doc.type == 'test'"
        )
    assert "vector cannot be empty" in str(exc_info.value)

    # Test with invalid top_k
    with pytest.raises(MCPError) as exc_info:
        await request_handler.hybrid_search(
            collection="test_collection",
            vector=[0.1, 0.2, 0.3],
            filter_query="doc.type == 'test'",
            top_k=0
        )
    assert "top_k must be positive" in str(exc_info.value)

@pytest.mark.asyncio
async def test_mcp_tool_decorator_mcp_error():
    """Test MCPError handling in the mcp_tool decorator."""
    @mcp_tool("Test description")
    async def failing_tool():
        raise MCPError("TEST_ERROR", "Test error")
    
    with pytest.raises(MCPError) as exc_info:
        await failing_tool()
    
    assert exc_info.value.code == "TEST_ERROR"
    assert "Test error" in str(exc_info.value) 

@pytest.mark.asyncio
async def test_handle_tool_call_validation_error(request_handler, mock_services):
    """Test handling validation error in tool call."""
    mock_services["vector_service"].search.side_effect = MCPError(
        "VALIDATION_ERROR",
        "Vector validation failed: vector cannot be empty",
        {"param": "vector"}
    )
    
    request = CallToolRequest(
        tool_name="vector_search",
        args={
            "collection": "test_collection",
            "vector": []  # Invalid empty vector
        }
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is False
    assert response["error"]["code"] == "VALIDATION_ERROR"
    assert response["error"]["message"] == "Vector validation failed: vector cannot be empty"
    assert response["error"]["details"] == {"param": "vector"} 

@pytest.mark.asyncio
async def test_handle_request_generic_error(request_handler):
    """Test handling generic error in request handler."""
    # Create a mock request that will trigger a generic exception
    request = CallToolRequest(
        tool_name="execute_query",
        args={}  # Missing required argument 'query'
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is False
    assert response["error"]["code"] == "INTERNAL_ERROR"
    assert str(response["error"]["message"]) != ""

@pytest.mark.asyncio
async def test_handle_tool_call_generic_error(request_handler, mock_services):
    """Test handling generic error in tool call."""
    # Make the service raise a generic exception
    mock_services["db_service"].execute_query.side_effect = TypeError("Invalid query type")
    
    request = CallToolRequest(
        tool_name="execute_query",
        args={
            "query": "FOR doc IN collection RETURN doc"
        }
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is False
    assert response["error"]["code"] == "INTERNAL_ERROR"
    assert "Invalid query type" in response["error"]["message"] 

@pytest.mark.asyncio
async def test_handle_request_validation_error(request_handler):
    """Test handling validation error in request handler."""
    # Create a request that will fail validation
    request = CallToolRequest(
        tool_name="execute_query",
        args={"invalid_arg": "value"}  # Missing required 'query' argument
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is False
    assert response["error"]["code"] == "INTERNAL_ERROR"
    assert str(response["error"]["message"]) != ""

@pytest.mark.asyncio
async def test_handle_tool_call_execution_error(request_handler, mock_services):
    """Test handling execution error in tool call."""
    # Make the service raise a runtime error
    mock_services["db_service"].execute_query.side_effect = RuntimeError("Execution failed")
    
    request = CallToolRequest(
        tool_name="execute_query",
        args={
            "query": "FOR doc IN collection RETURN doc"
        }
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is False
    assert response["error"]["code"] == "INTERNAL_ERROR"
    assert "Execution failed" in response["error"]["message"] 

@pytest.mark.asyncio
async def test_handle_request_unexpected_error(request_handler):
    """Test handling unexpected error in request handler."""
    # Create a request that will raise an unexpected error during validation
    request = MagicMock(spec=CallToolRequest)
    request.__class__ = CallToolRequest  # Make isinstance check work
    request.tool_name = "execute_query"  # Valid tool name
    request.args = {"query": "FOR doc IN collection RETURN doc"}  # Valid args
    
    # Mock the handle_tool_call method to raise an unexpected error
    original_handle_tool_call = request_handler.handle_tool_call
    request_handler.handle_tool_call = AsyncMock(side_effect=AttributeError("Unexpected attribute error"))
    
    try:
        response = await request_handler.handle_request(request)
        assert response["success"] is False
        assert response["error"]["code"] == "INTERNAL_ERROR"
        assert "Unexpected attribute error" in response["error"]["message"]
    finally:
        # Restore original method
        request_handler.handle_tool_call = original_handle_tool_call

@pytest.mark.asyncio
async def test_handle_tool_call_unexpected_error(request_handler, mock_services):
    """Test handling unexpected error in tool call."""
    # Make the service raise an unexpected error
    mock_services["db_service"].execute_query.side_effect = AttributeError("Service not ready")
    
    request = CallToolRequest(
        tool_name="execute_query",
        args={
            "query": "FOR doc IN collection RETURN doc"
        }
    )
    
    response = await request_handler.handle_request(request)
    assert response["success"] is False
    assert response["error"]["code"] == "INTERNAL_ERROR"
    assert "Service not ready" in response["error"]["message"] 

@pytest.mark.asyncio
async def test_handle_tool_call_error(request_handler):
    """Test handling error in handle_tool_call."""
    # Create a request that will raise an error during tool call
    request = CallToolRequest(
        tool_name="execute_query",
        args={"query": "FOR doc IN collection RETURN doc"}
    )
    
    # Mock the _tools dictionary to include a failing tool
    async def failing_tool(*args, **kwargs):
        raise Exception("Tool execution failed")
    failing_tool.is_tool = True
    failing_tool.description = "Test tool"
    request_handler._tools["execute_query"] = {
        "handler": failing_tool,
        "description": "Test tool",
        "schema": {}
    }
    
    response = await request_handler.handle_tool_call(request)
    assert response["success"] is False
    assert response["error"]["code"] == "INTERNAL_ERROR"
    assert "Tool execution failed" in response["error"]["message"] 