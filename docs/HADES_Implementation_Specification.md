# HADES Implementation Specification

## 1. Phased Implementation Approach

HADES follows a systematic, incremental implementation approach, building each component upon a validated foundation. This minimizes cascading errors and ensures system robustness. The implementation order is explicitly defined as: **Model Context Protocol (MCP) Server → PathRAG → Triple Context Restoration (TCR) → LLM Analysis → GraphCheck Validation**.

### 1.1 Model Context Protocol (MCP) Server Foundation (Initial Phase)

- **Initial Focus**: Basic WebSocket-based server implementation to enable communication between the LLM and tools
- **Authentication**: PostgreSQL-based system user ('hades' with password 'o$n^3W%QD0HGWxH!') with credentials managed via the password rotation script (`scripts/rotate_hades_password.sh`)
- **Database Integration**: 
  - Set up native PostgreSQL ('hades_test' database) for authentication and user management, using real connections for testing rather than mocks
  - Install and configure ArangoDB via native installation for Ubuntu Noble (24.04) compatibility with vector search capabilities
  - Use optimization techniques for maximum performance
- **Core Infrastructure**: Configure environment, system monitoring, and initial `.hades` directory structure
- **Cross-References**: 
  - See [HADES_Development_Phases.md](HADES_Development_phases.md) Phase 1 for timeline
  - See [README.md](README.md) for setup instructions

### 1.2 PathRAG Retrieval (Second Phase)

- **Core Logic**: Optimized graph traversals within ArangoDB to identify paths that link query-relevant nodes
- **Pruning Mechanism**: Assigns a "resource flow" score to potential paths; distant or low-flow edges get pruned to reduce noise
- **Memory-Enhanced Design**: Implements tiered memory management for efficient data access and context window optimization
- **Version-Aware Queries**: Supports querying the knowledge graph as it existed at specific versions or timestamps
- **Single-System Optimization**: Tailored for high-performance on local workstation with limited resources
- **Implementation References**: 
  - [PathRAG: Pruning Graph-based Retrieval Augmented Generation](https://arxiv.org/html/2502.14902v1)
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 2 for research foundation
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 2 for timeline
  - See [HADES_PathRAG_Implementation.md](HADES_PathRAG_Implementation.md) for detailed implementation plan

### 1.3 Triple Context Restoration (TCR) (Third Phase)

- **Context Enrichment**: For each triple (subject–predicate–object), TCR locates semantically similar sentences from corpus using ModernBERT-large
- **Vector Search Integration**: Introduced during vector retrieval to fetch additional contextual passages related to entities
- **Version-Aware Restoration**: Captures context changes over time for historical queries
- **Implementation References**: 
  - [How to Mitigate Information Loss in Knowledge Graphs for GraphRAG](https://arxiv.org/html/2501.15378v1)
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3 for pipeline integration
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 3 for timeline

### 1.4 LLM Analysis and Embedded Model Integration (Fourth Phase)

- **Joint Analysis**: The LLM synthesizes information from both PathRAG (graph structure) and TCR (contextual passages)
- **Response Generation**: Produces coherent answers based on combined graph and vector context
- **Human-Like Processing**: Mirrors how humans process structured and unstructured knowledge together
- **Embedded Model Architecture**:
  - Implements a model abstraction layer for flexible model swapping
  - Uses Ollama for initial implementation with future compatibility for other models
  - Provides entity extraction and relationship mapping through LLM-powered processing
  - Enhances the knowledge graph with intelligent structure extraction
- **Implementation References**:
  - Leverages vLLM for GPU-accelerated inference on RTX A6000s
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.1 for LLM details
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 3 for timeline
  - See [HADES_Embedded_Model_Implementation_Plan.md](HADES_Embedded_Model_Implementation_Plan.md) for detailed integration plan

### 1.5 GraphCheck Fact Verification (Fifth Phase)

- **Claim Extraction**: Parses the LLM's output into discrete factual claims
- **GNN-Based Verification**: Uses a graph neural network to compare claims with the knowledge graph
- **Feedback Loop**: If invalid claims are detected, the system prompts the LLM to revise the response or flags it for human review
- **Implementation References**: 
  - [GraphCheck: Breaking Long-Term Text Barriers with Extracted Knowledge Graph-Powered Fact-Checking](https://arxiv.org/html/2502.16514v1)
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3 for pipeline integration
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 4 for timeline

### 1.6 External Continual Learner (ECL) with `.hades` Directories (Integrated Throughout All Phases)

The ECL component is integrated throughout the implementation phases, with functionality expanded as the system matures. The ECL is integrated progressively during the PathRAG → TCR → LLM Analysis → GraphCheck implementation sequence:

- **`.hades` Directory Structure as Knowledge Silos**: 
  - **Hierarchical Organization**:
    - **Root `.hades`**: Project-level knowledge at repository root
    - **Subdirectory `.hades`**: Module-specific knowledge in code subdirectories
    - **Nested `.hades`**: Function or class-specific knowledge at deeper levels
  - **Directory Contents**:
    - `/raw`: Original documents and data files
    - `/embeddings`: Pre-computed embeddings for efficient retrieval
    - `/metadata`: Information about knowledge sources and relationships
    - `hades_config.json`: Configuration for this knowledge silo
  - **Cross-References**:
    - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.6 for system integration
    - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 1 for initial setup

- **Auto-Discovery System**: 
  - Uses filesystem events (via `inotify` on Linux) to detect changes in `.hades` directories
  - Maintains a cached index of `.hades` locations for performance
  - Implements precedence rules for overlapping knowledge domains
  - **Cross-References**:
    - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 2 for implementation timeline

- **Context-Aware Knowledge Management**: 
  - **Hierarchical Context**: Prioritizes local `.hades` directories for queries originating within their filesystem scope
  - **Context Fusion**: Weighs results from multiple `.hades` directories based on query relevance
  - **Conflict Resolution**: Manages overlapping knowledge with precedence rules
  - **Cross-References**:
    - See [README_VERSIONING.md](README_VERSIONING.md) for versioning integration

- **Actor-Network Theory (ANT) Implementation**:
  - Treats files, functions, and dependencies as "actors" in a dynamic knowledge system
  - Maps 2nd and 3rd-order dependencies through the knowledge graph
  - Predicts cascading effects of changes through graph traversal
  - **Cross-References**:
    - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 2.5 for theoretical foundation

- **Knowledge Upload Mechanism**:
  - Dropping files into `.hades` directories triggers automatic ingestion into ArangoDB
  - Git integration syncs knowledge with code changes
  - Automatic embedding updates when content changes
  - **Cross-References**:
    - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 4 for automation features

- **Incremental Learning**:
  - New documents/data maintain domain representations without retraining the LLM
  - Lazy-loading techniques avoid unnecessary computation
  - Update prioritization based on access patterns and recent changes
  - **Cross-References**:
    - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.6 for ECL details

- **User Memory System**:
  - **Secure File-Based Storage**:
    - Uses hashed API keys for user directory separation
    - Stores observations and conversation histories in structured directories
    - Monitors system information (users, groups) for context enrichment
  - **Entity-Relationship Model**:
    - Represents user memories as typed entities with atomic observations
    - Creates explicit relationships between memory entities
    - Supports vector embedding for semantic similarity search
  - **MCP Server Integration**:
    - Provides tools for retrieving and adding user memories
    - Leverages PathRAG for efficient memory retrieval
  - **Cross-References**:
    - See [docs/ECL_User_Memory_Implementation.md](docs/ECL_User_Memory_Implementation.md) for detailed implementation plan

- **Version-Controlled Knowledge**:
  - Processes diffs between versions to efficiently update domain representations
  - Generates training data from version changes
  - Tracks file history within each `.hades` directory for temporal context
  - **Cross-References**:
    - See [README_VERSIONING.md](README_VERSIONING.md) for version management details

- **Implementation References**: 
  - [In-context Continual Learning Assisted by an External Continual Learner](https://arxiv.org/html/2412.15563v1)
  - [Actor-Network Theory: Tracking Relations of Human and Non-Human Elements](https://www.sciencedirect.com/topics/computer-science/actor-network-theory)
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 2 for all research foundations

### 1.7 Differential Versioning System

- **Semantic Versioning**: Uses a major.minor.patch versioning scheme to track knowledge graph evolution
- **Change Logging**: Records detailed change information including document IDs, change types, and before/after values
- **Time-Travel Queries**: Enables querying the knowledge graph as it existed at specific versions or timestamps
- **Diff Generation**: Computes differences between versions to enable efficient incremental updates and training data generation
- **Version Visualization**: Provides tools for visualizing version history and knowledge graph evolution over time
- **Cross-References**:
  - See [README_VERSIONING.md](README_VERSIONING.md) for complete versioning documentation
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 4 for implementation timeline
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.7 for system integration

### 1.8 Data Ingestion Pipeline

- **Schema Validation**: Uses Pydantic models to validate incoming data against defined schemas
- **Multiple Validation Levels**: Supports strict, medium, and lenient validation modes to accommodate different data sources and quality requirements
- **Preprocessing & Normalization**: Automatically enriches and normalizes data during ingestion
- **Batch Processing**: Handles large data volumes efficiently through batched processing
- **Error Handling**: Provides comprehensive error tracking and reporting during all stages of ingestion
- **Cross-References**:
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 2 for initial implementation
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.8 for system integration

### 1.9 Security and Authentication

- **PostgreSQL-Based Authentication**: Uses PostgreSQL as the primary authentication database for both API and MCP servers
- **Dedicated System User**: Creates and manages 'hades' system user with credentials managed by the `scripts/rotate_hades_password.sh` script for secure database authentication
- **Test Database**: Configures 'hades_test' database with the 'hades' user as owner for consistent development testing
- **Role-Based Access Control**: Implements predefined roles (Admin, Editor, Analyst, Reader, API) with appropriate permission sets
- **Granular Permissions**: Defines specific permissions for different operations (read/write entities, manage users, etc.)
- **Token & API Key Management**: Provides secure creation, validation, and revocation of authentication tokens and API keys
- **Rate Limiting**: Prevents abuse through configurable rate limits per user or API key
- **Audit Logging**: Records all security-related events for monitoring and analysis
- **Encryption**: Secures sensitive data using modern cryptographic methods with key derivation
- **Password Rotation**: Implements a secure password management system (`rotate_hades_password.sh`) that:
  - Manages the 'hades' system user across OS, PostgreSQL, and ArangoDB
  - Generates strong random passwords
  - Updates credentials in all relevant environment files
  - Maintains synchronization across all system components
- **Cross-References**:
  - See [README.md](README.md) for security and password management overview
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 1 for initial security setup
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.9 for security layer details

### 1.10 Dual Server Architecture

- **API Server (`src/api/server.py`)**:
  - Implemented with FastAPI framework for robust, high-performance REST APIs
  - Provides traditional HTTP endpoints for client applications, web UIs, and third-party integrations
  - Handles standard request-response patterns with JSON payloads
  - Authentication via JWT tokens for stateless operation
  - Designed for general-purpose application interactions
  - **Cross-References**:
    - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 3 for implementation timeline
    - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.2 for server details

- **MCP Server (`src/mcp/server.py`)**:
  - Implemented with WebSockets for persistent, bidirectional communication
  - Specialized for direct model integration and tool execution
  - Maintains stateful sessions with connected clients
  - Provides a streamlined interface for registering and executing tools
  - Optimized for LLM integrations with lower latency requirements
  - **Cross-References**:
    - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 1 for initial implementation
    - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.2 for server details

- **Shared Components**:
  - Both servers use the same PostgreSQL-based authentication system ('hades' user with 'hades_test' database)
  - Common utilities for database connections and configuration
  - Real database connections for testing rather than mocks
  - Native ArangoDB installation for optimal performance on Ubuntu Noble (24.04)
  - Shared data models for authentication and authorization
  - Consistent security practices across both implementations

## 2. Code Samples and Implementation Patterns

Below are illustrative snippets showing how components will be implemented in a phased approach, following the development timeline outlined in [HADES_Development_phases.md](HADES_Development_phases.md).

### 2.1 Phase 1-2: PathRAG Implementation

```python
# Phase 1-2: Implementation of PathRAG as an MCP tool
def pathrag_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute PathRAG retrieval - first core component to be implemented.
    
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
    
    # Optimized for single-system architecture
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
```

### 2.2 Phase 3: Triple Context Restoration Implementation

```python
# Phase 3: Implementation of TCR as an MCP tool
def tcr_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute TCR to restore context around graph triples - second core component.
    
    Args:
        args: TCR parameters
        
    Returns:
        Enriched context for graph relationships
    """
    entity_id = args.get("entity_id", "")
    relationship_types = args.get("relationship_types", [])
    max_context_items = args.get("max_context_items", 5)
    as_of_version = args.get("as_of_version")
    
    # Get relevant triples from PathRAG results
    triples = self.knowledge_graph.get_entity_relationships(
        entity_id=entity_id,
        relationship_types=relationship_types,
        as_of_version=as_of_version
    )
    
    # Restore natural language context for each triple
    enriched_context = self.tcr.restore_context(
        triples=triples,
        max_context_items=max_context_items
    )
    
    return {
        "entity_id": entity_id,
        "enriched_context": enriched_context,
        "context_count": len(enriched_context),
        "version": as_of_version
    }
```

### 2.3 Phase 4: GraphCheck Implementation

```python
# Phase 4: Implementation of GraphCheck as an MCP tool (final component)
def graphcheck_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute GraphCheck verification - final validation component.
    
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
```

### 2.4 Security and PostgreSQL Authentication Integration

```python
# Security permission check using PostgreSQL for authentication with 'hades' user
def has_permission(self, user_or_key: str, permission: Permission, is_api_key: bool = False) -> bool:
    """
    Check if a user or API key has a specific permission.
    Uses real PostgreSQL connection with 'hades' database user.
    
    Args:
        user_or_key: Username or API key ID
        permission: Permission to check
        is_api_key: Whether the identifier is an API key ID
        
    Returns:
        True if the user/key has the permission, False otherwise
    """
    # Use PostgreSQL for auth with 'hades' user (not SQLite as in early prototype)
    import psycopg2
    from psycopg2.extras import Json
    
    # Connect to hades_test database with hades user
    # Password is managed by scripts/rotate_hades_password.sh and stored in environment
    import os
    conn = psycopg2.connect(
        dbname="hades_test",
        user="hades",
        password=os.environ.get("HADES_PG_PASSWORD"),  # Set by password rotation script
        host="localhost"
    )
    cursor = conn.cursor()
    
    if is_api_key:
        cursor.execute("""
        SELECT permissions FROM api_keys WHERE key_id = %s AND is_active = TRUE
        """, (user_or_key,))
    else:
        cursor.execute("""
        SELECT permissions FROM users WHERE username = %s AND is_active = TRUE
        """, (user_or_key,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False
    
    permissions = result[0]  # PostgreSQL JSON type automatically converted
    
    # Check if the permission is in the list
    return permission.name in permissions
```

### 2.5 Database Setup and Integration

```python
# Setup script for native PostgreSQL and ArangoDB installation
def setup_databases():
    """
    Set up databases for HADES with native installations:
    - PostgreSQL with 'hades' user for authentication
    - ArangoDB for graph-based knowledge storage on Ubuntu Noble (24.04)
    Uses real connections rather than mocks for testing.
    """
    import os
    import subprocess
    import time
    
    # Create hades system user if it doesn't exist
    subprocess.run(
        "id -u hades || sudo useradd -m -s /bin/bash hades",
        shell=True, check=True
    )
    
    # Set up PostgreSQL for the hades user
    print("Setting up PostgreSQL with 'hades' user and 'hades_test' database...")
    
    # Use the rotate_hades_password.sh script to manage passwords securely
    # This avoids hardcoding passwords and ensures consistent credential management
    script_path = os.path.join(PROJECT_DIR, "scripts", "rotate_hades_password.sh")
    subprocess.run(
        f"sudo {script_path}",  # This will generate a secure random password
        shell=True, check=True
    )
    
    # The password is now managed by the rotation script
    subprocess.run(
        "sudo -u postgres psql -c \"CREATE DATABASE hades_test WITH OWNER hades;\" || true",
        shell=True, check=True
    )
    subprocess.run(
        "sudo -u postgres psql -c \"ALTER ROLE hades SUPERUSER;\" || true",
        shell=True, check=True
    )
    
    # Set up ArangoDB natively for Ubuntu Noble (24.04)
    print("Setting up ArangoDB for Ubuntu Noble (24.04)...")
    
    # Install ArangoDB using the official repository
    print("Installing ArangoDB from the official repository...")
    subprocess.run(
        """sudo apt update && \
        curl -OL https://download.arangodb.com/arangodb319/DEBIAN/Release.key && \
        sudo apt-key add - < Release.key && \
        echo 'deb https://download.arangodb.com/arangodb319/DEBIAN/ /' | \
        sudo tee /etc/apt/sources.list.d/arangodb.list && \
        sudo apt update && \
        sudo apt install -y arangodb3""",
        shell=True, check=True
    )
    print("Successfully installed ArangoDB native package")
    
    # Get the ArangoDB password from environment (set by the password rotation script)
    # First source the env file created by the rotation script
    source_cmd = f"source {PROJECT_DIR}/.env && echo $HADES_ARANGO_PASSWORD"
    arango_password = subprocess.check_output(
        source_cmd, shell=True, executable='/bin/bash', text=True
    ).strip()
    
    # Configure ArangoDB with the secure password
    print("Configuring ArangoDB with secure password...")
    subprocess.run(
        f"sudo arango-secure-installation --password '{arango_password}'",
        shell=True, check=True
    )
    
    # Enable and start ArangoDB service
    print("Enabling and starting ArangoDB service...")
    subprocess.run(
        "sudo systemctl enable arangodb3 && sudo systemctl start arangodb3",
        shell=True, check=True
    )
    
    # Wait for ArangoDB to initialize
    print("Waiting for ArangoDB to start...")
    time.sleep(5)  # Give ArangoDB time to initialize
    
    # Verify ArangoDB is running
    print("Verifying ArangoDB connection...")
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("localhost", 8529))
    s.close()
    print("ArangoDB is running and accessible on port 8529")
    
    print("Databases setup complete!")
    print("PostgreSQL: 'hades' user and 'hades_test' database")
    print("ArangoDB: Should be accessible on port 8529 (check warnings if any)")
```
```

## 3. Revised Implementation Strategy

The HADES system follows a more incremental, risk-mitigating implementation approach based on analysis of the project's strengths and challenges. This revised strategy focuses on delivering a working MVP first, then gradually enhancing it with more advanced features. This pragmatic approach ensures each component builds upon a validated foundation while providing tangible value at each stage.

### 3.1 Phase 1: Foundation and Core PathRAG (Weeks 1-6)

#### 3.1.1 Model Abstraction Layer (Weeks 1-2)
- **Goal**: Create a working model interface that enables entity extraction
- **Key Components**:
  - `LLMProcessor` abstract base class implementation
  - Ollama adapter with proper error handling
  - ModelFactory with configuration loading
  - Simple entity extraction CLI testing tool
- **Key Success Metrics**: Successfully extract entities from sample documents
- **Cross-References**:
  - See [HADES_Embedded_Model_Implementation_Plan.md](HADES_Embedded_Model_Implementation_Plan.md) for design details
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.5 for component integration

#### 3.1.2 Basic PathRAG Implementation (Weeks 3-4)
- **Goal**: Create minimal viable PathRAG that can retrieve knowledge paths
- **Key Components**:
  - Simplified ArangoDB graph schema optimized for single-system operation
  - Basic entity storage and relationship mapping
  - Efficient path finding algorithms with configurable depth
  - Simple path scoring based on relationship types
- **Key Success Metrics**: Successful path retrieval with >70% relevance on test queries
- **Cross-References**:
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.3 for PathRAG design
  - Reference papers: [PathRAG: Pruning Graph-based Retrieval Augmented Generation](https://arxiv.org/html/2502.14902v1)

#### 3.1.3 Knowledge Ingestion Pipeline (Weeks 5-6)
- **Goal**: Create an end-to-end pipeline for document ingestion
- **Key Components**:
  - Document processor with basic chunking strategies
  - Entity extractor using the model abstraction layer
  - Relationship mapper for basic triple extraction
  - Knowledge graph manager for ArangoDB interactions
  - MCP tool enhancements for data ingestion and retrieval
- **Key Success Metrics**: Successfully process 5+ document types with proper entity/relationship extraction
- **Cross-References**:
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.1 for MCP server integration

### 3.2 Phase 2: Query Enhancement and Minimal Versioning (Weeks 7-12)

#### 3.2.1 Basic Triple Context Restoration (TCR) (Weeks 7-8)
- **Goal**: Implement simplified context restoration without feedback loops
- **Key Components**:
  - Context storage mechanism in ArangoDB
  - Basic embedding generation for context passages
  - Context retrieval for enhancing graph triples
- **Key Success Metrics**: Improved answer quality in 60% of test cases compared to basic PathRAG
- **Cross-References**:
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.4 for TCR design
  - Reference papers: [How to Mitigate Information Loss in Knowledge Graphs for GraphRAG](https://arxiv.org/html/2501.15378v1)

#### 3.2.2 Simple Versioning System (Weeks 9-10)
- **Goal**: Implement basic versioning without full differential capabilities
- **Key Components**:
  - Simplified version tracking schema in ArangoDB
  - Version metadata for entities and relationships
  - Basic time-travel queries with version filtering
  - API endpoints for version-aware queries
- **Key Success Metrics**: Successfully retrieve knowledge as it existed at different points in time
- **Cross-References**:
  - See [README_VERSIONING.md](README_VERSIONING.md) for versioning design

#### 3.2.3 Query Understanding and Processing (Weeks 11-12)
- **Goal**: Enhance query capabilities with semantic understanding
- **Key Components**:
  - Query decomposition for complex questions
  - Query understanding component using the LLM
  - Result composition logic for multi-part answers
  - Explanation generation for retrieved paths
- **Key Success Metrics**: Handle 80% of test complex queries correctly
- **Cross-References**:
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.5 for LLM integration

### 3.3 Phase 3: Performance Optimization and Resource Management (Weeks 13-18)

#### 3.3.1 Performance Monitoring Infrastructure (Weeks 13-14)
- **Goal**: Implement comprehensive monitoring for system resources
- **Key Components**:
  - Resource monitoring for CPU, GPU, and RAM
  - Performance metrics collection
  - Basic dashboard for resource visualization
  - Logging for performance bottlenecks
- **Key Success Metrics**: Accurate telemetry data for all system components
- **Cross-References**:
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 4 for related tasks

#### 3.3.2 Memory and Resource Optimization (Weeks 15-16)
- **Goal**: Optimize memory usage and resource allocation
- **Key Components**:
  - RAM-based caching for frequently accessed embeddings
  - GPU memory management for model inference
  - Basic resource scheduling based on priority
  - Database query optimization
- **Key Success Metrics**: 30%+ improvement in throughput or latency for core operations
- **Cross-References**:
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 4 for optimization tasks

#### 3.3.3 `.hades` Directory Implementation (Weeks 17-18)
- **Goal**: Implement basic `.hades` directory structure for knowledge organization
- **Key Components**:
  - Directory structure and file organization
  - File system monitoring (inotify)
  - Auto-discovery for `.hades` directories
  - Metadata tracking for knowledge sources
- **Key Success Metrics**: Successfully organize and retrieve knowledge from `.hades` directories
- **Cross-References**:
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.6 for ECL integration

### 3.4 Phase 4: Integration and Advanced Features (Weeks 19-24)

#### 3.4.1 Full TCR with Query Feedback (Weeks 19-20)
- **Goal**: Enhance TCR with query-driven feedback
- **Key Components**:
  - Feedback loops for context enhancement
  - Query-specific context retrieval
  - Dynamic context expansion based on query
- **Key Success Metrics**: Further 20% improvement in answer quality over basic TCR
- **Cross-References**:
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.4 for component design

#### 3.4.2 Simplified GraphCheck Implementation (Weeks 21-22)
- **Goal**: Create basic fact verification without full GNN complexity
- **Key Components**:
  - Claim extraction from LLM outputs
  - Simple graph-based verification logic
  - Feedback mechanism for invalid claims
- **Key Success Metrics**: Detect 70% of factual inaccuracies in test cases
- **Cross-References**:
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.6 for component design
  - Reference papers: [GraphCheck: Breaking Long-Term Text Barriers with Extracted Knowledge Graph-Powered Fact-Checking](https://arxiv.org/html/2502.16514v1)

#### 3.4.3 User Interface and Documentation (Weeks 23-24)
- **Goal**: Create comprehensive documentation and basic UI
- **Key Components**:
  - API documentation for all endpoints
  - User guide with examples
  - Basic web interface for system interaction
  - Deployment documentation
- **Key Success Metrics**: Successfully onboard new users with documentation alone
- **Cross-References**:
  - See [docs/windsurf_integration.md](docs/windsurf_integration.md) for MCP integration details

### 3.5 Phase 5: Advanced Features and Scaling (Weeks 25-30)

#### 3.5.1 Differential Versioning Enhancement (Weeks 25-26)
- **Goal**: Implement full differential versioning system
- **Key Components**:
  - Enhanced version tracking with diff generation
  - Efficient storage for version history
  - Training data generation from diffs
  - Version history visualization
- **Key Success Metrics**: Efficient storage and retrieval of version history with minimal overhead
- **Cross-References**:
  - See [README_VERSIONING.md](README_VERSIONING.md) for complete versioning documentation

#### 3.5.2 Full GraphCheck with Simplified GNN (Weeks 27-28)
- **Goal**: Enhance fact verification with graph neural networks
- **Key Components**:
  - Simplified GNN for fact verification
  - Training on existing knowledge graph data
  - Confidence scoring for verification results
- **Key Success Metrics**: 85%+ accuracy in fact verification
- **Cross-References**:
  - See [HADES_Architecture_Overview.md](HADES_Architecture_Overview.md) Section 3.6 for component design

#### 3.5.3 System Scaling and Deployment Options (Weeks 29-30)
- **Goal**: Provide scaling options beyond single-system deployment
- **Key Components**:
  - Performance characteristics documentation
  - Deployment guides for various hardware configurations
  - Optional distributed components 
  - Testing with larger knowledge graphs
- **Key Success Metrics**: Successfully deploy and benchmark on different hardware configurations
- **Cross-References**:
  - See [HADES_Development_phases.md](HADES_Development_phases.md) Phase 6 for scaling tasks

## 4. Database Schema and Configuration

HADES uses a combination of PostgreSQL for authentication and ArangoDB as its primary knowledge store. Both databases are installed natively on Ubuntu Noble (24.04) for optimal performance and direct hardware access. The native installation provides several advantages:

1. **Lower System Overhead** - Direct access to system resources without container layers
2. **Optimized Performance** - Direct memory and CPU access for graph operations
3. **Fine-tuned Configuration** - Ability to optimize database parameters for specific hardware

The enhanced database schema includes:

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

## 5. Environment Configuration

For development and production, HADES is configured using environment variables, which are stored in a `.env` file at the repository root. This configuration supports native installations on Ubuntu Noble (24.04) for optimal performance.

### Authentication Database (PostgreSQL)

```env
HADES_MCP__AUTH__DB_TYPE=postgresql
HADES_PG_HOST=localhost
HADES_PG_PORT=5432
HADES_PG_USER=hades
# Password is managed by scripts/rotate_hades_password.sh
# HADES_PG_PASSWORD=[managed by password rotation script]
HADES_PG_DATABASE=hades_test
```

> **Important**: All passwords are managed by the `scripts/rotate_hades_password.sh` script. DO NOT manually set passwords in environment files.

### Knowledge Graph Database (ArangoDB)

```env
HADES_ARANGO_HOST=localhost
HADES_ARANGO_PORT=8529
HADES_ARANGO_USER=root
# Password is managed by scripts/rotate_hades_password.sh
# HADES_ARANGO_PASSWORD=[managed by password rotation script]
HADES_ARANGO_DATABASE=hades_kg
```

### Configuration Best Practices

Additional configuration tips to maximize performance on bare-metal installations:

#### ArangoDB Native Optimizations

```bash
# CPU and Memory optimizations - add to /etc/arangodb3/arangod.conf
[rocksdb]
# Optimize for high-performance servers with plenty of RAM
block-cache-size = 4294967296  # 4GB cache (adjust based on available RAM)
max-total-wal-size = 1073741824  # 1GB (adjust based on write load)

# Thread pool sizes for optimal core utilization
[server]
minimal-threads = 16  # Adjust based on available CPU cores

# Performance tuning for vector indexing
[index]
# HNSW optimization for vector search performance
hnsw.max-connections = 64  # Increase for better quality, decrease for better speed
```

#### PostgreSQL Native Optimizations

```bash
# Add to /etc/postgresql/14/main/postgresql.conf
shared_buffers = 2GB  # 25% of RAM for dedicated DB servers
work_mem = 128MB  # Increase for complex queries
maintenance_work_mem = 256MB  # For index building
effective_cache_size = 6GB  # 75% of RAM for DB caching estimates
random_page_cost = 1.1  # Lower for SSD/NVMe storage
```

Note: For production environments, passwords should be managed securely through environment variables or secret management systems, not hardcoded in configuration files.

## 6. `.hades` Directory Implementation Details

### Directory Structure

The `.hades` directories follow a standardized structure across all locations:

```
/path/to/project_or_module/
├── .hades/
│   ├── raw/
│   │   ├── document1.md
│   │   ├── document2.pdf
│   │   └── ...
│   ├── embeddings/
│   │   ├── embeddings.pkl
│   │   ├── vector_store.faiss
│   │   └── ...
│   ├── metadata/
│   │   ├── sources.json
│   │   ├── relationships.json
│   │   └── ...
│   └── hades_config.json
├── src/
│   ├── module1/
│   │   ├── .hades/
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── ...
```

### Configuration File Format

Each `.hades` directory contains a `hades_config.json` file that defines its behavior:

```json
{
  "name": "module_knowledge_silo",
  "description": "Knowledge related to the specific module functionality",
  "precedence": 50,  // Higher values take precedence when multiple silos match
  "parent_silo": "../../../.hades",  // Path to parent silo for inheritance
  "embedding_model": "modernbert-large",
  "update_triggers": [
    {
      "type": "file_change",
      "pattern": "*.py",
      "action": "update_embeddings"
    },
    {
      "type": "git_commit",
      "action": "sync_with_kg"
    }
  ],
  "relationships": [
    {
      "target_silo": "../../module2/.hades",
      "relationship_type": "depends_on",
      "strength": 0.8
    }
  ]
}
```

### ECL Processing Algorithm

The ECL processes `.hades` directories using the following algorithm:

```python
def process_hades_directories(query, context):
    # Find relevant .hades directories based on the query context
    relevant_silos = discover_hades_directories(context.working_directory)
    
    # Determine precedence and filtering
    active_silos = filter_and_prioritize_silos(relevant_silos, query)
    
    # Extract embeddings from each relevant silo
    combined_results = []
    for silo in active_silos:
        # Get embeddings and metadata from the silo
        silo_results = query_silo(silo, query)
        combined_results.extend(silo_results)
    
    # Perform context fusion to merge and rank results
    fused_results = context_fusion(combined_results, query)
    
    return fused_results
```

## 7. Deployment Configuration

### Native Service Management for Development

For development on Ubuntu Noble (24.04), native service management provides optimal performance and direct hardware access through systemd:

```bash
# systemd service configuration for ArangoDB
# File: /etc/systemd/system/arangodb3.service
# This is managed by the standard installation, but can be customized for HADES needs

[Unit]
Description=ArangoDB Server
After=network.target

[Service]
Type=simple
User=arangodb
Group=arangodb
Environment=GLIBCXX_FORCE_NEW=1
ExecStart=/usr/sbin/arangod --server.uid arangodb --server.gid arangodb
LimitNOFILE=131072
LimitNPROC=131072
TimeoutSec=0
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
# systemd service configuration for PostgreSQL
# This is managed by the standard installation, but shown here for reference

# Start, stop, or restart services with:
sudo systemctl start postgresql
sudo systemctl start arangodb3

# Check service status with:
sudo systemctl status postgresql
sudo systemctl status arangodb3

# Enable services to start at boot:
sudo systemctl enable postgresql
sudo systemctl enable arangodb3
```
```

### Initialization Scripts

```bash
#!/bin/bash
# setup_environment.sh

# Get project root directory
PROJECT_DIR="$(dirname "$(readlink -f "$0")")/.."

# Create system user if it doesn't exist
id -u hades &>/dev/null || sudo useradd -m -s /bin/bash hades

# Set up PostgreSQL role and database
sudo -u postgres psql -c "CREATE ROLE hades WITH LOGIN;" || true
sudo -u postgres psql -c "CREATE DATABASE hades_test WITH OWNER hades;" || true
sudo -u postgres psql -c "ALTER ROLE hades SUPERUSER;" || true

# Run password rotation script to securely set and manage passwords
# This will create the .env file with secure random passwords
echo "Running password rotation script to set up secure credentials..."
sudo "${PROJECT_DIR}/scripts/rotate_hades_password.sh"

# Additional environment variables (passwords managed by rotation script)
cat >> "${PROJECT_DIR}/.env" << EOL
HADES_MCP__AUTH__DB_TYPE=postgresql
HADES_PG_HOST=localhost
HADES_PG_PORT=5432
HADES_PG_USER=hades
HADES_PG_DATABASE=hades_test

HADES_ARANGO_HOST=localhost
HADES_ARANGO_PORT=8529
HADES_ARANGO_USER=root
HADES_ARANGO_PASSWORD=rootpassword
HADES_ARANGO_DATABASE=hades_kg
EOL

echo "Environment setup complete. Configuration written to .env"
```

## 8. MCP Integration Details

### 8.1 MCP Server Overview

- **Single Entry Point**: The MCP server is the only interface exposed externally, guaranteeing standardization and security.
- **Transport Mechanisms**: HADES follows the recommended approach of using SSE (Server-Sent Events) and/or stdio for model access, as documented at [https://modelcontextprotocol.io/docs/concepts/transports](https://modelcontextprotocol.io/docs/concepts/transports).
- **Class-Based Design**: Implements a modular, class-based design for better organization and extension.

### 8.2 MCP Tools Implementation

- **PathRAG, GraphCheck, TCR Tools**: Each functional block is registered as a "tool" with a well-defined JSON schema specifying inputs and outputs.
- **Resource Exposure**: ArangoDB data can be exposed as resources (e.g., `kg://entities`) that can be read or updated through standardized MCP resource requests.
- **Version-Aware Tools**: All tools support version and timestamp parameters for time-travel operations.
- **ECL Tools**: Added methods for incremental updates and training data generation from version diffs.

### 8.3 Security and Authentication

- **Role-Based Access Control**: Implements RBAC with predefined roles and granular permissions.
- **Token-Based Access**: Uses hashed tokens stored in a dedicated SQLite database exclusively for authentication and rate limiting, keeping this separate from the main knowledge store.
- **API Key Management**: Provides secure API key generation, validation, and revocation with expiration support.
- **Rate Limiting**: Each user and API key can be restricted to a set number of requests per time window to prevent abuse.
- **Audit Logging**: Records all security events for monitoring and compliance.
- **Encryption**: Secures sensitive data using Fernet symmetric encryption with key derivation.

## 9. API and Interface Specifications

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
