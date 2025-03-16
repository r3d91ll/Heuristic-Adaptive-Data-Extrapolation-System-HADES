from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum

# Base Models
class MCPMessage(BaseModel):
    """Base class for all MCP messages."""
    request_id: Optional[str] = None

# Authentication Models
class AuthenticationRequest(MCPMessage):
    """Model for authentication requests."""
    type: Literal["authenticate"] = "authenticate"
    username: str
    password: str

class AuthenticationResponse(MCPMessage):
    """Model for authentication responses."""
    success: bool
    token: Optional[str] = None
    error: Optional[str] = None

# Tool Call Models
class ToolCallRequest(MCPMessage):
    """Model for tool call requests."""
    type: Literal["tool_call"] = "tool_call"
    tool: str
    params: Dict[str, Any] = {}

class ToolCallResponse(MCPMessage):
    """Base model for tool call responses."""
    success: bool
    error: Optional[str] = None

# Database Tool Models
class ShowDatabasesResponse(ToolCallResponse):
    """Response for the show_databases tool."""
    databases: Optional[Dict[str, List[str]]] = None

# Keep the original models for compatibility with other parts of the system
class QueryRequest(BaseModel):
    """
    Pydantic model for query requests.
    
    Args:
        query: The natural language query to process
        domain_filter: Optional domain to filter results by (default is None)
    """
    query: str
    domain_filter: Optional[str] = None

class QueryResponse(BaseModel):
    """
    Pydantic model for query responses.
    
    Args:
        response: The processed response from the query
        verified_claims: List of verified claims related to the query
    """
    response: str
    verified_claims: List[Dict[str, Any]]