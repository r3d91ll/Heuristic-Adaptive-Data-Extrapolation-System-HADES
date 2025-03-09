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
from src.utils.versioning import KGVersion, ChangeLog
from src.utils.version_sync import version_sync

# Import tools that will be registered with the MCP server
from src.rag.pathrag import execute_pathrag
from src.db.connection import connection
from src.core.orchestrator import orchestrator
from src.graphcheck.fact_verification import GraphCheck
from src.ecl.continual_learner import ExternalContinualLearner
from src.tcr.context_restoration import TripleContextRestoration
from src.core.data_ingestion import DataIngestionManager

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

class MCPServer:
    """
    MCP Server implementation for standardized interface to HADES components.
    """
    
    def __init__(self):
        self.logger = logger
        self.db = connection
        self.change_log = ChangeLog(self.db)
        
        # Initialize components
        self.path_rag = PathRAG(self.db)
        self.graph_check = GraphCheck(self.db)
        self.ecl = ExternalContinualLearner(self.db)
        self.tcr = TripleContextRestoration(self.db)
        self.data_ingestion = DataIngestionManager(self.db)
        
        # Register tools
        self.tools = {
            "kg_query": self.kg_query,
            "kg_query_as_of_version": self.kg_query_as_of_version,
            "kg_version_compare": self.kg_version_compare,
            "kg_version_history": self.kg_version_history,
            "kg_generate_training_data": self.kg_generate_training_data,
            "pathrag": self.pathrag_tool,
            "graphcheck": self.graphcheck_tool,
            "tcr": self.tcr_tool,
            "ecl_update": self.ecl_update_tool,
            "ingest_data": self.ingest_data_tool,
        }
    
    def register_tools(self, mcp_server_instance):
        """
        Register all tools with the MCP server instance.
        
        Args:
            mcp_server_instance: The MCP server instance to register tools with
        """
        for tool_name, tool_func in self.tools.items():
            # In a real implementation, this would use the MCP server registration API
            self.logger.info(f"Registered tool: {tool_name}")
    
    def kg_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a query against the knowledge graph.
        
        Args:
            args: Query parameters
            
        Returns:
            Query results
        """
        query = args.get("query", "")
        collection = args.get("collection", "entities")
        limit = args.get("limit", 10)
        
        self.logger.info(f"Executing KG query: {query}")
        
        aql_query = f"""
        FOR doc IN {collection}
            SEARCH ANALYZER(TOKENS(@query, "text_en") ALL IN TOKENS(doc.name, "text_en"), "text_en")
            LIMIT @limit
            RETURN doc
        """
        
        cursor = self.db.aql.execute(aql_query, bind_vars={"query": query, "limit": limit})
        results = [doc for doc in cursor]
        
        return {"results": results, "count": len(results)}
    
    def kg_query_as_of_version(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a version-aware query against the knowledge graph.
        
        Args:
            args: Query parameters including version
            
        Returns:
            Query results
        """
        query = args.get("query", "")
        collection = args.get("collection", "entities")
        limit = args.get("limit", 10)
        version = args.get("version")
        timestamp = args.get("timestamp")
        
        self.logger.info(f"Executing version-aware KG query: {query}")
        
        # Version-aware parameters
        bind_vars = {"query": query, "limit": limit}
        version_clause = ""
        
        if version:
            kg_version = KGVersion.parse(version)
            bind_vars["version"] = kg_version.to_string()
            version_clause = "FILTER doc.version <= @version"
        elif timestamp:
            bind_vars["timestamp"] = timestamp
            version_clause = "FILTER doc.created_at <= @timestamp"
        
        aql_query = f"""
        FOR doc IN {collection}
            {version_clause}
            SEARCH ANALYZER(TOKENS(@query, "text_en") ALL IN TOKENS(doc.name, "text_en"), "text_en")
            LIMIT @limit
            RETURN doc
        """
        
        cursor = self.db.aql.execute(aql_query, bind_vars=bind_vars)
        results = [doc for doc in cursor]
        
        return {
            "results": results, 
            "count": len(results),
            "version": version,
            "timestamp": timestamp
        }
    
    def kg_version_compare(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two versions of a document.
        
        Args:
            args: Comparison parameters
            
        Returns:
            Comparison results
        """
        collection = args.get("collection")
        document_id = args.get("document_id")
        version1 = args.get("version1")
        version2 = args.get("version2")
        
        self.logger.info(f"Comparing versions: {version1} and {version2} for {document_id}")
        
        v1 = KGVersion.parse(version1)
        v2 = KGVersion.parse(version2)
        
        diff = self.change_log.compare_document_versions(collection, document_id, v1, v2)
        
        return {
            "document_id": document_id,
            "version1": version1,
            "version2": version2,
            "diff": diff
        }
    
    def kg_version_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get version history of a document.
        
        Args:
            args: History parameters
            
        Returns:
            Version history
        """
        collection = args.get("collection")
        document_id = args.get("document_id")
        
        self.logger.info(f"Getting version history for {document_id}")
        
        history = self.change_log.get_document_history(collection, document_id)
        
        return {
            "document_id": document_id,
            "history": history
        }
    
    def kg_generate_training_data(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate training data from changes between versions.
        
        Args:
            args: Training data parameters
            
        Returns:
            Generated training data
        """
        start_version = args.get("start_version")
        end_version = args.get("end_version")
        
        self.logger.info(f"Generating training data from {start_version} to {end_version}")
        
        training_data = self.ecl.generate_training_data(start_version, end_version)
        
        return {
            "start_version": start_version,
            "end_version": end_version,
            "training_examples": training_data,
            "count": len(training_data)
        }
    
    def pathrag_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute PathRAG retrieval.
        
        Args:
            args: PathRAG parameters
            
        Returns:
            Retrieved paths
        """
        query = args.get("query", "")
        max_paths = args.get("max_paths", 5)
        domain_filter = args.get("domain_filter")
        as_of_version = args.get("as_of_version")
        as_of_timestamp = args.get("as_of_timestamp")
        
        self.logger.info(f"Executing PathRAG for query: {query}")
        
        paths = self.path_rag.retrieve(
            query=query,
            max_paths=max_paths,
            domain_filter=domain_filter,
            as_of_version=as_of_version,
            as_of_timestamp=as_of_timestamp
        )
        
        pruned_paths = self.path_rag.prune_paths(paths)
        
        return {
            "query": query,
            "paths": pruned_paths,
            "count": len(pruned_paths),
            "version": as_of_version,
            "timestamp": as_of_timestamp
        }
    
    def graphcheck_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute GraphCheck verification.
        
        Args:
            args: GraphCheck parameters
            
        Returns:
            Verification results
        """
        text = args.get("text", "")
        as_of_version = args.get("as_of_version")
        as_of_timestamp = args.get("as_of_timestamp")
        
        self.logger.info(f"Executing GraphCheck for text: {text[:100]}...")
        
        claims = self.graph_check.extract_claims(text)
        verified_claims = self.graph_check.verify_claims(
            claims=claims,
            as_of_version=as_of_version,
            as_of_timestamp=as_of_timestamp
        )
        
        return {
            "text": text,
            "claims": verified_claims,
            "count": len(verified_claims),
            "verified_count": sum(c["is_verified"] for c in verified_claims),
            "version": as_of_version,
            "timestamp": as_of_timestamp
        }
    
    def tcr_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Triple Context Restoration.
        
        Args:
            args: TCR parameters
            
        Returns:
            Restored context
        """
        triple_id = args.get("triple_id")
        query_feedback = args.get("query_feedback", False)
        query = args.get("query", "")
        
        self.logger.info(f"Executing TCR for triple: {triple_id}")
        
        context = self.tcr.restore_context(triple_id)
        
        if query_feedback and query:
            feedback = self.tcr.apply_query_feedback(query, context)
            return {
                "triple_id": triple_id,
                "context": context,
                "feedback": feedback
            }
        
        return {
            "triple_id": triple_id,
            "context": context
        }
    
    def ecl_update_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute ECL update.
        
        Args:
            args: ECL parameters
            
        Returns:
            Update results
        """
        if "domain_name" in args:
            domain_name = args.get("domain_name")
            self.logger.info(f"Updating domain embeddings for: {domain_name}")
            result = self.ecl.maintain_domain_embeddings(domain_name)
            return result
        elif "start_version" in args and "end_version" in args:
            start_version = args.get("start_version")
            end_version = args.get("end_version")
            self.logger.info(f"Processing incremental updates from {start_version} to {end_version}")
            result = self.ecl.process_incremental_updates(start_version, end_version)
            return result
        else:
            return {"error": "Missing required parameters"}
    
    def ingest_data_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute data ingestion.
        
        Args:
            args: Ingestion parameters
            
        Returns:
            Ingestion results
        """
        data = args.get("data", {})
        data_type = args.get("data_type", "entity")
        validation_level = args.get("validation_level", "strict")
        update_version = args.get("update_version", True)
        
        self.logger.info(f"Ingesting {data_type} data with validation level: {validation_level}")
        
        result = self.data_ingestion.ingest(
            data=data,
            data_type=data_type,
            validation_level=validation_level,
            update_version=update_version
        )
        
        return result


# --- MCP Endpoints ---

@app.get("/tools")
async def get_tools(api_key: APIKey = Depends(get_current_key)) -> Dict[str, List[Tool]]:
    """Get all registered tools."""
    server = MCPServer()
    server.register_tools(app)
    return {"tools": list(server.tools.values())}


@app.post("/tools/{tool_name}")
async def call_tool(
    tool_name: str, 
    request: Request,
    api_key: APIKey = Depends(get_current_key),
    _: None = Depends(check_rate_limit),
) -> Response:
    """Call a specific tool by name."""
    server = MCPServer()
    if tool_name not in server.tools:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        body = await request.json()
        arguments = body.get("arguments", {})
        
        # Tool dispatch logic
        if tool_name == "pathrag":
            result = server.pathrag_tool(arguments)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "tcr":
            result = server.tcr_tool(arguments)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "graphcheck":
            result = server.graphcheck_tool(arguments)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "ecl_update":
            result = server.ecl_update_tool(arguments)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "ingest_data":
            result = server.ingest_data_tool(arguments)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "kg_version_compare":
            result = server.kg_version_compare(arguments)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "kg_version_history":
            result = server.kg_version_history(arguments)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "kg_query_as_of_version":
            result = server.kg_query_as_of_version(arguments)
            return Response(
                content=json.dumps({"result": result, "error": None}),
                media_type="application/json",
            )
        
        elif tool_name == "kg_generate_training_data":
            result = server.kg_generate_training_data(arguments)
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
