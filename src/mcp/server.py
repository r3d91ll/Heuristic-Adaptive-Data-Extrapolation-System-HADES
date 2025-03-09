"""
MCP Server implementation for HADES.

This module implements the Model Context Protocol server that provides
a standardized interface for LLM access to HADES components.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.mcp.auth import get_current_key, check_rate_limit, auth_db, APIKey

from src.utils.logger import get_logger
from src.utils.scheduler import start_scheduler, stop_scheduler
from src.utils.versioning import KGVersion
from src.utils.version_sync import version_sync

# Import tools that will be registered with the MCP server
from src.rag.pathrag import execute_pathrag
from src.db.connection import connection
from src.core.orchestrator import orchestrator

logger = get_logger(__name__)

app = FastAPI(
    title="HADES MCP Server",
    description="Model Context Protocol server for HADES",
    version="0.1.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Lifecycle Events ---

@app.on_event("startup")
async def startup_event():
    """Initialize components on server startup."""
    logger.info("Starting HADES MCP server")
    
    # Initialize database
    try:
        connection.initialize_database()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Start the background task scheduler
    try:
        start_scheduler()
        logger.info("Background task scheduler started")
    except Exception as e:
        logger.error(f"Failed to start background tasks: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on server shutdown."""
    logger.info("Shutting down HADES MCP server")
    
    # Stop the background task scheduler
    try:
        stop_scheduler()
        logger.info("Background task scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping background tasks: {e}")


# --- MCP Models ---

class Tool(BaseModel):
    """MCP Tool definition."""
    name: str
    description: str
    parameters: Dict[str, str]


class ToolCall(BaseModel):
    """MCP Tool call request."""
    tool: str
    arguments: Dict[str, Any]


class ToolResponse(BaseModel):
    """MCP Tool call response."""
    result: Any
    error: Optional[str] = None


class QueryRequest(BaseModel):
    """Query request to HADES."""
    query: str
    max_results: int = Field(default=5, ge=1, le=20)
    domain_filter: Optional[str] = None


class QueryResponse(BaseModel):
    """Query response from HADES."""
    answer: str
    sources: List[Dict[str, Any]]
    paths: Optional[List[Dict[str, Any]]] = None


# --- MCP Server Implementation ---

# Dictionary of registered tools
tools: Dict[str, Tool] = {}


def register_tool(name: str, description: str, parameters: Dict[str, str]) -> None:
    """Register a tool with the MCP server."""
    tools[name] = Tool(name=name, description=description, parameters=parameters)
    logger.info(f"Registered tool: {name}")


# --- Tool Registrations ---

# Register the PathRAG tool
register_tool(
    name="pathrag",
    description="Graph-based path retrieval",
    parameters={
        "query": "string",
        "max_paths": "number",
        "domain_filter": "string",
    },
)

# Register the TCR tool
register_tool(
    name="tcr",
    description="Triple Context Restoration",
    parameters={
        "triple": "object",
        "limit": "number",
    },
)

# Register the GraphCheck tool
register_tool(
    name="graphcheck",
    description="Fact verification",
    parameters={
        "text": "string",
    },
)

# Register the ECL tool
register_tool(
    name="ecl_ingest",
    description="Ingest new document",
    parameters={
        "document": "object",
    },
)

register_tool(
    name="ecl_suggest",
    description="Suggest relevant documents",
    parameters={
        "query": "string",
        "limit": "number",
    },
)

# Add versioning tools
register_tool(
    name="kg_version_compare",
    description="Compare two versions of a document in the knowledge graph",
    parameters={
        "collection": "string",
        "document_id": "string",
        "version1": "string",
        "version2": "string",
    },
)

register_tool(
    name="kg_version_history",
    description="Get version history of a document in the knowledge graph",
    parameters={
        "collection": "string",
        "document_id": "string",
    },
)

register_tool(
    name="kg_query_as_of_version",
    description="Query the knowledge graph as it existed at a specific version",
    parameters={
        "query": "string",
        "version": "string",
        "max_results": "number",
        "domain_filter": "string",
    },
)

register_tool(
    name="kg_generate_training_data",
    description="Generate training data from knowledge graph changes",
    parameters={
        "start_version": "string",
        "end_version": "string",
        "output_file": "string",
    },
)


# --- MCP Endpoints ---

@app.get("/tools")
async def get_tools(api_key: APIKey = Depends(get_current_key)) -> Dict[str, List[Tool]]:
    """Get all registered tools."""
    return {"tools": list(tools.values())}


@app.post("/tools/{tool_name}")
async def call_tool(
    tool_name: str, 
    request: Request,
    api_key: APIKey = Depends(get_current_key),
    _: None = Depends(check_rate_limit),
) -> Response:
    """Call a specific tool by name."""
    if tool_name not in tools:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        body = await request.json()
        arguments = body.get("arguments", {})
        
        # Tool dispatch logic
        if tool_name == "pathrag":
            result = execute_pathrag(
                query=arguments.get("query", ""),
                max_paths=arguments.get("max_paths", 5),
                domain_filter=arguments.get("domain_filter"),
            )
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "tcr":
            from src.tcr.restoration import tcr
            triple = arguments.get("triple", {})
            limit = arguments.get("limit", 3)
            result = tcr.find_similar_context(triple, limit)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "graphcheck":
            from src.graphcheck.verification import graphcheck
            text = arguments.get("text", "")
            result = graphcheck.verify_text(text)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "ecl_ingest":
            from src.ecl.learner import ecl
            document = arguments.get("document", {})
            result = ecl.ingest_new_document(document)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "ecl_suggest":
            from src.ecl.learner import ecl
            query = arguments.get("query", "")
            limit = arguments.get("limit", 5)
            result = ecl.suggest_relevant_documents(query, limit)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "kg_version_compare":
            collection = arguments.get("collection", "")
            document_id = arguments.get("document_id", "")
            version1 = arguments.get("version1", "")
            version2 = arguments.get("version2", "")
            
            if not all([collection, document_id, version1, version2]):
                raise HTTPException(
                    status_code=400, 
                    detail="Missing required parameters"
                )
            
            result = connection.compare_versions(
                collection=collection,
                document_id=document_id,
                version1=version1,
                version2=version2
            )
            
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "kg_version_history":
            collection = arguments.get("collection", "")
            document_id = arguments.get("document_id", "")
            
            if not all([collection, document_id]):
                raise HTTPException(
                    status_code=400, 
                    detail="Missing required parameters"
                )
            
            result = connection.get_document_history(
                collection=collection,
                document_id=document_id
            )
            
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "kg_query_as_of_version":
            query = arguments.get("query", "")
            version = arguments.get("version", "")
            max_results = arguments.get("max_results", 5)
            domain_filter = arguments.get("domain_filter", None)
            
            if not query or not version:
                raise HTTPException(
                    status_code=400, 
                    detail="Query and version are required"
                )
            
            # Use the orchestrator to handle the query with version
            result = orchestrator.process_query(
                query=query,
                max_results=max_results,
                domain_filter=domain_filter,
                as_of_version=version
            )
            
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "kg_generate_training_data":
            start_version = arguments.get("start_version", "")
            end_version = arguments.get("end_version", "")
            output_file = arguments.get("output_file", None)
            
            if not start_version or not end_version:
                raise HTTPException(
                    status_code=400, 
                    detail="Start and end versions are required"
                )
            
            result = version_sync.generate_training_data_from_diff(
                start_version=start_version,
                end_version=end_version,
                output_file=output_file
            )
            
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        # If we get here, the tool is registered but not implemented
        raise HTTPException(
            status_code=501, 
            detail=f"Tool '{tool_name}' is registered but not implemented"
        )
    
    except Exception as e:
        logger.error(f"Error calling tool '{tool_name}': {e}")
        return Response(
            content=json.dumps({"result": None, "error": str(e)}),
            media_type="application/json",
        )


@app.post("/query")
async def query(
    request: QueryRequest, 
    api_key: APIKey = Depends(get_current_key),
    _: None = Depends(check_rate_limit),
) -> QueryResponse:
    """Main query endpoint for HADES."""
    # Use the orchestrator to process the query
    result = orchestrator.process_query(
        query=request.query,
        max_results=request.max_results,
        domain_filter=request.domain_filter,
    )
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {result.get('error', 'Unknown error')}"
        )
    
    # Extract sources from the results
    sources = []
    
    # Add any contexts from TCR
    for path in result.get("paths", []):
        for context in path.get("contexts", []):
            if context.get("source"):
                sources.append({
                    "title": context.get("source", {}).get("title", "Unknown"),
                    "url": context.get("source", {}).get("url", ""),
                    "text": context.get("text", ""),
                })
    
    # Add any relevant documents from ECL
    for doc in result.get("relevant_documents", []):
        sources.append({
            "title": doc.get("title", "Unknown"),
            "domain": doc.get("domain", ""),
            "relevance": doc.get("relevance", 0),
            "text": doc.get("summary", ""),
        })
    
    return QueryResponse(
        answer=result.get("answer", "No answer available"),
        sources=sources,
        paths=result.get("paths", []),
    )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/auth/keys")
async def create_api_key(
    name: str, 
    expiry_days: Optional[int] = None, 
    admin_key: APIKey = Depends(get_current_key)
) -> Dict[str, Any]:
    """Create a new API key. Requires admin privileges."""
    # In a production setup, you would check admin_key.key_id against a list of admin keys
    # For now, we'll allow any authenticated user to create keys
    key_id, api_key = auth_db.create_api_key(name, expiry_days)
    
    return {
        "key_id": key_id,
        "api_key": api_key,
        "name": name,
        "expires_at": (datetime.now() + timedelta(days=expiry_days)).isoformat() if expiry_days else None
    }


# --- Main entry point ---

def main() -> None:
    """Run the MCP server."""
    import uvicorn
    from src.utils.config import config
    
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    
    # Create a default API key if none exists
    if getattr(config.mcp, "auth_enabled", False):
        with auth_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM api_keys")
            row = cursor.fetchone()
            if row and row["count"] == 0:
                key_id, api_key = auth_db.create_api_key(
                    name="default", 
                    expiry_days=30
                )
                logger.info(f"Created default API key: {api_key} (expires in 30 days)")
    
    logger.info(f"Starting MCP server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
