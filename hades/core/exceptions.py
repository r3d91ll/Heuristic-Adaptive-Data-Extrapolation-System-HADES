"""Custom exceptions for the HADES system."""

from typing import Optional, Dict, Any

class MCPError(Exception):
    """Base exception class for MCP errors."""
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary format."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        } 