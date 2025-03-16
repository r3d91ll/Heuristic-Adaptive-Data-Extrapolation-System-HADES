from pydantic import BaseModel
from typing import Any, Dict, List, Optional

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