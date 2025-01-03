"""Tests for custom exceptions."""

from hades.core.exceptions import MCPError

def test_mcp_error_basic():
    """Test basic MCPError creation."""
    error = MCPError("TEST_ERROR", "Test error message")
    assert error.code == "TEST_ERROR"
    assert error.message == "Test error message"
    assert error.details == {}

def test_mcp_error_with_details():
    """Test MCPError with details."""
    details = {"key": "value", "number": 42}
    error = MCPError("TEST_ERROR", "Test error message", details)
    assert error.code == "TEST_ERROR"
    assert error.message == "Test error message"
    assert error.details == details

def test_mcp_error_to_dict():
    """Test MCPError to_dict method."""
    details = {"key": "value"}
    error = MCPError("TEST_ERROR", "Test error message", details)
    error_dict = error.to_dict()
    
    assert error_dict == {
        "code": "TEST_ERROR",
        "message": "Test error message",
        "details": details
    }

def test_mcp_error_str():
    """Test MCPError string representation."""
    error = MCPError("TEST_ERROR", "Test error message")
    assert str(error) == "Test error message" 