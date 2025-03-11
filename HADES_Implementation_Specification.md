# HADES_Implementation_Specification.md

## 1. Detailed Component Implementations

### 1.1 PathRAG Retrieval

- **Core Logic**: Uses graph traversals within ArangoDB to identify paths that link query-relevant nodes.
- **Pruning Mechanism**: Assigns a "resource flow" score to potential paths; distant or low-flow edges get pruned to reduce noise.
- **Version-Aware Queries**: Supports querying the knowledge graph as it existed at specific versions or timestamps using version filters.
- **Implementation References**: [PathRAG: Pruning Graph-based Retrieval Augmented Generation](https://arxiv.org/html/2502.14902v1)

### 1.2 Triple Context Restoration (TCR) and Query-Driven Feedback

- **Context Enrichment**: For each triple (subject–predicate–object), TCR locates a semantically similar sentence from the original corpus using ModernBERT-large embeddings.
- **Iterative Query Feedback**: If a partial LLM output indicates missing knowledge, TCR performs a dense vector search to fetch new, relevant context. Missing or newly discovered triples get added to the knowledge graph.
- **Version Integration**: Captures context changes over time, allowing restoration of relevant context as it existed at specific versions.
- **Implementation References**: [How to Mitigate Information Loss in Knowledge Graphs for GraphRAG](https://arxiv.org/html/2501.15378v1)

### 1.3 GraphCheck Fact Verification

- **Claim Extraction**: Parses the LLM's output into discrete factual claims.
- **GNN-Based Verification**: Uses a graph neural network (GNN) to compare claims with the knowledge graph.
- **Feedback Loop**: If invalid claims are detected, the system prompts the LLM to revise the response or flags it for human review.
- **Version-Aware Verification**: Verifies claims against the knowledge graph as it existed at specific points in time.
- **Implementation References**: [GraphCheck: Breaking Long-Term Text Barriers with Extracted Knowledge Graph-Powered Fact-Checking](https://arxiv.org/html/2502.16514v1)

### 1.4 External Continual Learner (ECL)

- **Domain Clustering**: Maintains domain embeddings in a separate module, referencing them to identify relevant knowledge sources.
- **Gaussians for Domain Representation**: Summarizes each domain with a distribution of embeddings; queries are filtered or ranked based on Mahalanobis distance.
- **Incremental Updates**: Ingests new documents/data to keep domain representations in sync without retraining the LLM.
- **Version-Driven Updates**: Processes changes between versions to efficiently update domain representations and generate training data.
- **Implementation References**: [In-context Continual Learning Assisted by an External Continual Learner](https://arxiv.org/html/2412.15563v1)

### 1.5 Differential Versioning System

- **Semantic Versioning**: Uses a major.minor.patch versioning scheme to track knowledge graph evolution.
- **Change Logging**: Records detailed change information including document IDs, change types, and before/after values.
- **Time-Travel Queries**: Enables querying the knowledge graph as it existed at specific versions or timestamps.
- **Diff Generation**: Computes differences between versions to enable efficient incremental updates and training data generation.
- **Version Visualization**: Provides tools for visualizing version history and knowledge graph evolution over time.

### 1.6 Data Ingestion Pipeline

- **Schema Validation**: Uses Pydantic models to validate incoming data against defined schemas.
- **Multiple Validation Levels**: Supports strict, medium, and lenient validation modes to accommodate different data sources and quality requirements.
- **Preprocessing & Normalization**: Automatically enriches and normalizes data during ingestion.
- **Batch Processing**: Handles large data volumes efficiently through batched processing.
- **Error Handling**: Provides comprehensive error tracking and reporting during all stages of ingestion.

### 1.7 Security and Authentication

- **Role-Based Access Control**: Implements predefined roles (Admin, Editor, Analyst, Reader, API) with appropriate permission sets.
- **Granular Permissions**: Defines specific permissions for different operations (read/write entities, manage users, etc.).
- **Token & API Key Management**: Provides secure creation, validation, and revocation of authentication tokens and API keys.
- **Rate Limiting**: Prevents abuse through configurable rate limits per user or API key.
- **Audit Logging**: Records all security-related events for monitoring and analysis.
- **Encryption**: Secures sensitive data using modern cryptographic methods with key derivation.

## 2. Code Samples and Patterns

Below are illustrative snippets showing how components may be registered as "tools" under the Model Context Protocol (MCP) interface.

```python
# Example: Updated PathRAG with version-aware queries
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

# Example: GraphCheck with version-aware verification
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

# Example: Security permission check
def has_permission(self, user_or_key: str, permission: Permission, is_api_key: bool = False) -> bool:
    """
    Check if a user or API key has a specific permission.
    
    Args:
        user_or_key: Username or API key ID
        permission: Permission to check
        is_api_key: Whether the identifier is an API key ID
        
    Returns:
        True if the user/key has the permission, False otherwise
    """
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    if is_api_key:
        cursor.execute('''
        SELECT permissions FROM api_keys WHERE key_id = ? AND is_active = 1
        ''', (user_or_key,))
    else:
        cursor.execute('''
        SELECT permissions FROM users WHERE username = ? AND is_active = 1
        ''', (user_or_key,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False
    
    permissions = json.loads(result[0])
    
    # Check if the permission is in the list
    return permission.name in permissions
```

## 3. Database Schema and Configuration

HADES uses ArangoDB as its primary knowledge store. The enhanced schema includes:

```javascript
// Creating document collections
db._create('entities');
db._create('contexts');
db._create('domains');
db._create('versions');
db._create('changes');

// Creating edge collections for relationships
db._createEdgeCollection('relationships');
db._createEdgeCollection('entity_domains');
db._createEdgeCollection('entity_contexts');

// Example indexes
db.entities.ensureIndex({ type: 'persistent', fields: ['name', 'type'] });
db.entities.ensureIndex({ type: 'persistent', fields: ['version'] });
db.relationships.ensureIndex({ type: 'persistent', fields: ['_from', '_to', 'type'] });
db.relationships.ensureIndex({ type: 'persistent', fields: ['version'] });
db.contexts.ensureIndex({ type: 'fulltext', fields: ['text'] });
db.changes.ensureIndex({ type: 'persistent', fields: ['document_id', 'version'] });
```

**Configuration Hints**:

- Increase memory limits for RocksDB in ArangoDB for large knowledge bases.
- Employ appropriate indexing (persistent, full-text) to optimize graph queries and textual lookups.
- Store metadata with edges (e.g., "relationship type" or "weight") for advanced path pruning.
- Include version metadata with each document and edge to enable efficient time-travel queries.
- Consider time-based sharding for very large change logs to maintain performance over time.

## 4. MCP Integration Details

### 4.1 MCP Server Overview

- **Single Entry Point**: The MCP server is the only interface exposed externally, guaranteeing standardization and security.
- **Transport Mechanisms**: HADES follows the recommended approach of using SSE (Server-Sent Events) and/or stdio for model access, as documented at [https://modelcontextprotocol.io/docs/concepts/transports](https://modelcontextprotocol.io/docs/concepts/transports).
- **Class-Based Design**: Implements a modular, class-based design for better organization and extension.

### 4.2 MCP Tools Implementation

- **PathRAG, GraphCheck, TCR Tools**: Each functional block is registered as a "tool" with a well-defined JSON schema specifying inputs and outputs.
- **Resource Exposure**: ArangoDB data can be exposed as resources (e.g., `kg://entities`) that can be read or updated through standardized MCP resource requests.
- **Version-Aware Tools**: All tools support version and timestamp parameters for time-travel operations.
- **ECL Tools**: Added methods for incremental updates and training data generation from version diffs.

### 4.3 Security and Authentication

- **Role-Based Access Control**: Implements RBAC with predefined roles and granular permissions.
- **Token-Based Access**: Uses hashed tokens stored in a dedicated SQLite database exclusively for authentication and rate limiting, keeping this separate from the main knowledge store.
- **API Key Management**: Provides secure API key generation, validation, and revocation with expiration support.
- **Rate Limiting**: Each user and API key can be restricted to a set number of requests per time window to prevent abuse.
- **Audit Logging**: Records all security events for monitoring and compliance.
- **Encryption**: Secures sensitive data using Fernet symmetric encryption with key derivation.

## 5. API and Interface Specifications

In addition to (or underneath) the MCP server, HADES may optionally expose RESTful or WebSocket endpoints for specialized integrations:

1. **REST Endpoints (FastAPI Example)**:

    ```python
    @app.post("/api/query")
    async def process_query(
        query: str,
        max_results: int = 5,
        domain_filter: Optional[str] = None,
        as_of_version: Optional[str] = None,
        as_of_timestamp: Optional[str] = None,
        api_key: APIKey = Depends(get_current_key)
    ):
        # Authenticate and check permissions
        if not security_manager.has_permission(api_key.key_id, Permission.EXECUTE_QUERIES, is_api_key=True):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Calls PathRAG, GraphCheck, etc., under the hood with version parameters
        result = orchestrator.process_query(
            query=query,
            max_results=max_results,
            domain_filter=domain_filter,
            as_of_version=as_of_version,
            as_of_timestamp=as_of_timestamp
        )
        
        return {"result": result}
    ```

2. **WebSocket for IRC Integration**:

    ```python
    @app.websocket("/ws/irc")
    async def irc_socket(websocket: WebSocket):
        # Authenticate connection
        credentials = await websocket.receive_json()
        auth_result = security_manager.authenticate(
            credentials.get("username"),
            credentials.get("password")
        )
        
        if auth_result["status"] != "success":
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        await websocket.accept()
        
        while True:
            data = await websocket.receive_json()
            # Example: send or receive IRC messages via the HADES pipeline
            # with appropriate permission checks
            ...
    ```

3. **MCP Tools**:
    - Registered within the server with appropriate permission checks.
    - Provide standardized methods for knowledge retrieval, verification, and version management.
    - Support version and timestamp parameters for time-travel operations.

4. **Versioning API Endpoints**:

    ```python
    @app.get("/api/versions")
    async def list_versions(
        api_key: APIKey = Depends(get_current_key)
    ):
        # Check permissions
        if not security_manager.has_permission(api_key.key_id, Permission.ACCESS_HISTORY, is_api_key=True):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # List available versions
        versions = version_manager.list_versions()
        return {"versions": versions}
    
    @app.post("/api/training-data")
    async def generate_training_data(
        start_version: str,
        end_version: str,
        api_key: APIKey = Depends(get_current_key)
    ):
        # Check permissions
        if not security_manager.has_permission(api_key.key_id, Permission.TRAIN_MODELS, is_api_key=True):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Generate training data from version diffs
        training_data = ecl.generate_training_data(start_version, end_version)
        return {"training_data": training_data}
    ```

## References

To maintain a unified reference set, this specification again includes the core research upon which HADES is built:

- **PathRAG**: [Pruning Graph-based RAG with Relational Paths](https://arxiv.org/html/2502.14902v1)  
- **TCR**: [How to Mitigate Information Loss in Knowledge Graphs for GraphRAG](https://arxiv.org/html/2501.15378v1)  
- **GraphCheck**: [Breaking Long-Term Text Barriers with Knowledge Graph-Powered Fact-Checking](https://arxiv.org/html/2502.16514v1)  
- **ECL**: [In-context Continual Learning Assisted by an External Continual Learner](https://arxiv.org/html/2412.15563v1)  
- **MCP**: [https://modelcontextprotocol.io](https://modelcontextprotocol.io)
