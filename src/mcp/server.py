from fastapi import FastAPI, HTTPException, Depends
from src.utils.logger import get_logger
from src.core.security import Security
from src.core.data_ingestion import DataIngestion
from src.core.orchestrator import HADESOrchestrator
from src.db.connection import get_db_connection
from src.mcp.models import QueryRequest, QueryResponse  # Import QueryRequest and QueryResponse
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

app = FastAPI()
security = Security()
data_ingestion = DataIngestion()
orchestrator = HADESOrchestrator()

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        A simple response indicating the server is up and running
    """
    logger.info("Health check requested")
    return {"status": "healthy"}

def get_current_key(token: str):
    """
    Get the current API key for authentication.
    
    Args:
        token: The JWT token to authenticate
    
    Returns:
        The API key if valid, otherwise raises an HTTPException
    """
    logger.info(f"Getting current key for token: {token}")
    result = security.authorize(token, "get_current_key")
    if not result["success"]:
        logger.error(f"Authorization failed for get_current_key - {result.get('error')}")
        raise HTTPException(status_code=403, detail=result.get("error"))
    
    return result["key"]

@app.post("/api/authenticate")
async def authenticate(username: str, password: str):
    """
    Authenticate a user.
    
    Args:
        username: The username to authenticate
        password: The password for the user
        
    Returns:
        Authentication status and metadata
    """
    logger.info(f"Authenticating user: {username}")
    
    result = security.authenticate(username, password)
    if not result["success"]:
        logger.error(f"Authentication failed for user: {username} - {result.get('error')}")
        raise HTTPException(status_code=401, detail=result.get("error"))
    
    logger.info(f"User {username} authenticated successfully")
    return {
        "token": result["token"]
    }

@app.post("/api/authorize")
async def authorize(token: str, action: str):
    """
    Authorize a user for an action.
    
    Args:
        token: The JWT token to authorize
        action: The action to authorize the user for
        
    Returns:
        Authorization status and metadata
    """
    logger.info(f"Authorizing token for action: {action}")
    
    result = security.authorize(token, action)
    if not result["success"]:
        logger.error(f"Authorization failed - {result.get('error')}")
        raise HTTPException(status_code=403, detail=result.get("error"))
    
    logger.info(f"Token authorized successfully for action: {action}")
    return {
        "authorized": result["authorized"]
    }

@app.post("/api/ingest")
async def ingest_data(data: List[Dict[str, Any]], domain: str, token: str):
    """
    Ingest new data into the knowledge graph.
    
    Args:
        data: List of data points to ingest
        domain: Domain to which the data belongs
        token: JWT token for authorization
        
    Returns:
        Ingestion status and metadata
    """
    logger.info(f"Ingesting {len(data)} data points into domain: {domain}")
    
    # Authorize the user
    auth_result = security.authorize(token, "ingest")
    if not auth_result["success"]:
        logger.error(f"Authorization failed for ingest - {auth_result.get('error')}")
        raise HTTPException(status_code=403, detail=auth_result.get("error"))
    
    result = data_ingestion.ingest_data(data, domain)
    if not result["success"]:
        logger.error(f"Ingestion failed - {result.get('error')}")
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    logger.info(f"Data ingestion successful for domain: {domain} with {result['ingested_count']} data points")
    return {
        "ingested_count": result["ingested_count"],
        "domain": domain
    }

@app.post("/api/query", response_model=QueryResponse)
async def process_query(query_request: QueryRequest, token: str):
    """
    Process a natural language query through the HADES pipeline.
    
    Args:
        query_request: The request containing the query and optional domain filter
        token: JWT token for authorization
        
    Returns:
        Processed response and metadata
    """
    logger.info(f"Processing query: {query_request.query}")
    
    # Authorize the user
    auth_result = security.authorize(token, "query")
    if not auth_result["success"]:
        logger.error(f"Authorization failed for query - {auth_result.get('error')}")
        raise HTTPException(status_code=403, detail=auth_result.get("error"))
    
    result = orchestrator.process_query(query_request.query, query_request.domain_filter)
    if not result["success"]:
        logger.error(f"Query processing failed - {result.get('error')}")
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    logger.info(f"Query processed successfully: {query_request.query}")
    return QueryResponse(
        response=result["response"],
        verified_claims=result["verified_claims"]
    )

# Placeholder for execute_pathrag function if needed
@app.post("/api/execute_pathrag")
async def execute_pathrag(token: str, data: Dict[str, Any]):
    """
    Execute a specific tool or operation.
    
    Args:
        token: The JWT token for authorization
        data: Data required for the operation
        
    Returns:
        Execution status and metadata
    """
    logger.info(f"Executing pathrag with data: {data}")
    
    # Authorize the user
    auth_result = security.authorize(token, "execute_pathrag")
    if not auth_result["success"]:
        logger.error(f"Authorization failed for execute_pathrag - {auth_result.get('error')}")
        raise HTTPException(status_code=403, detail=auth_result.get("error"))
    
    # Placeholder logic for execute_pathrag
    result = {"success": True, "result": "Pathrag executed successfully"}
    logger.info(f"Pathrag execution successful with data: {data}")
    return result
