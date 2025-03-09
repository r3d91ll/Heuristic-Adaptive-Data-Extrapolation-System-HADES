# HADES_Implementation_Specification.md

## 1. Detailed Component Implementations

### 1.1 PathRAG Retrieval

- **Core Logic**: Uses graph traversals within ArangoDB to identify paths that link query-relevant nodes.
- **Pruning Mechanism**: Assigns a “resource flow” score to potential paths; distant or low-flow edges get pruned to reduce noise.
- **Implementation References**: [PathRAG: Pruning Graph-based Retrieval Augmented Generation](https://arxiv.org/html/2502.14902v1)

### 1.2 Triple Context Restoration (TCR) and Query-Driven Feedback

- **Context Enrichment**: For each triple (subject–predicate–object), TCR locates a semantically similar sentence from the original corpus using ModernBERT-large embeddings.
- **Iterative Query Feedback**: If a partial LLM output indicates missing knowledge, TCR performs a dense vector search to fetch new, relevant context. Missing or newly discovered triples get added to the knowledge graph.
- **Implementation References**: [How to Mitigate Information Loss in Knowledge Graphs for GraphRAG](https://arxiv.org/html/2501.15378v1)

### 1.3 GraphCheck Fact Verification

- **Claim Extraction**: Parses the LLM’s output into discrete factual claims.
- **GNN-Based Verification**: Uses a graph neural network (GNN) to compare claims with the knowledge graph.
- **Feedback Loop**: If invalid claims are detected, the system prompts the LLM to revise the response or flags it for human review.
- **Implementation References**: [GraphCheck: Breaking Long-Term Text Barriers with Extracted Knowledge Graph-Powered Fact-Checking](https://arxiv.org/html/2502.16514v1)

### 1.4 External Continual Learner (ECL)

- **Domain Clustering**: Maintains domain embeddings in a separate module, referencing them to identify relevant knowledge sources.
- **Gaussians for Domain Representation**: Summarizes each domain with a distribution of embeddings; queries are filtered or ranked based on Mahalanobis distance.
- **Incremental Updates**: Ingests new documents/data to keep domain representations in sync without retraining the LLM.
- **Implementation References**: [In-context Continual Learning Assisted by an External Continual Learner](https://arxiv.org/html/2412.15563v1)

## 2. Code Samples and Patterns

Below are illustrative snippets showing how components may be registered as “tools” under the Model Context Protocol (MCP) interface.

```java
// Example: Registering PathRAG as a tool in the MCP server
var pathRagTool = new McpServerFeatures.SyncToolRegistration(
    new Tool("pathrag", "Graph-based path retrieval", Map.of(
        "query", "string",
        "max_paths", "number",
        "domain_filter", "string"
    )),
    arguments -> {
        // Implement PathRAG retrieval logic here
        String query = arguments.get("query").toString();
        // ...
        return new CallToolResult(retrievalResult, false);
    }
);

// Example: GraphCheck fact-verification tool
var graphCheckTool = new McpServerFeatures.SyncToolRegistration(
    new Tool("graphcheck", "Fact verification", Map.of(
        "claims", "array",
        "evidence", "string"
    )),
    arguments -> {
        // Implement GNN-based fact verification
        // ...
        return new CallToolResult(verificationResult, false);
    }
);
```

## 3. Database Schema and Configuration

HADES uses ArangoDB as its primary knowledge store. A recommended schema might include:

```javascript
// Creating document collections
db._create('entities');
db._create('contexts');
db._create('domains');

// Creating edge collections for relationships
db._createEdgeCollection('relationships');
db._createEdgeCollection('entity_domains');
db._createEdgeCollection('entity_contexts');

// Example indexes
db.entities.ensureIndex({ type: 'persistent', fields: ['name', 'type'] });
db.relationships.ensureIndex({ type: 'persistent', fields: ['_from', '_to', 'type'] });
db.contexts.ensureIndex({ type: 'fulltext', fields: ['text'] });
```

**Configuration Hints**:

- Increase memory limits for RocksDB in ArangoDB for large knowledge bases.
- Employ appropriate indexing (persistent, full-text) to optimize graph queries and textual lookups.
- Store metadata with edges (e.g., “relationship type” or “weight”) for advanced path pruning.

## 4. MCP Integration Details

### 4.1 MCP Server Overview

- **Single Entry Point**: The MCP server is the only interface exposed externally, guaranteeing standardization and security.
- **Transport Mechanisms**: HADES follows the recommended approach of using SSE (Server-Sent Events) and/or stdio for model access, as documented at [https://modelcontextprotocol.io/docs/concepts/transports](https://modelcontextprotocol.io/docs/concepts/transports).

### 4.2 MCP Tools Implementation

- **PathRAG, GraphCheck, TCR Tools**: Each functional block is registered as a “tool” with a well-defined JSON schema specifying inputs and outputs.
- **Resource Exposure**: ArangoDB data can be exposed as resources (e.g., `kg://entities`) that can be read or updated through standardized MCP resource requests.

### 4.3 Security and Authentication

- **Token-Based Access**: Implement hashed tokens stored in a lightweight local database (SQLite or ArangoDB), enabling or disabling keys as needed.
- **Rate Limiting**: Each key can be restricted to a set number of requests per time window to prevent abuse.

## 5. API and Interface Specifications

In addition to (or underneath) the MCP server, HADES may optionally expose RESTful or WebSocket endpoints for specialized integrations:

1. **REST Endpoints (FastAPI Example)**:

    ```python
    from fastapi import FastAPI

    app = FastAPI()

    @app.post("/api/query")
    async def process_query(query: str):
        # Calls PathRAG, GraphCheck, etc., under the hood
        ...
        return {"result": "Answer from HADES"}
    ```

2. **WebSocket for IRC Integration**:

    ```python
    @app.websocket("/ws/irc")
    async def irc_socket(websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await websocket.receive_json()
            # Example: send or receive IRC messages via the HADES pipeline
            ...
    ```

3. **MCP Tools**:
    - Registered within the server (as shown in the code samples above).
    - Provide standardized methods for knowledge retrieval and verification.

## References

To maintain a unified reference set, this specification again includes the core research upon which HADES is built:

- **PathRAG**: [Pruning Graph-based RAG with Relational Paths](https://arxiv.org/html/2502.14902v1)  
- **TCR**: [How to Mitigate Information Loss in Knowledge Graphs for GraphRAG](https://arxiv.org/html/2501.15378v1)  
- **GraphCheck**: [Breaking Long-Term Text Barriers with Knowledge Graph-Powered Fact-Checking](https://arxiv.org/html/2502.16514v1)  
- **ECL**: [In-context Continual Learning Assisted by an External Continual Learner](https://arxiv.org/html/2412.15563v1)  
- **MCP**: [https://modelcontextprotocol.io](https://modelcontextprotocol.io)
