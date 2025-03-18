# HADES Architecture Overview

## 1. Introduction and System Purpose

HADES is designed as a single-system Machine Intelligence (MI) that merges a locally-deployed Large Language Model (LLM) with a graph-based knowledge repository, optimized for execution on a high-end workstation (AMD Threadripper 7960X + 256GB RAM + 2x RTX A6000 GPUs). By integrating multiple research innovations—PathRAG, Triple Context Restoration (TCR), GraphCheck, and an External Continual Learner (ECL)—into a cohesive pipeline following a logical implementation order (MCP → PathRAG → TCR → LLM Analysis → GraphCheck), HADES efficiently retrieves, verifies, and enriches knowledge while intelligently managing system resources.

### Key Goals and Purpose

- **Efficient Single-System MI:** Optimize all components to run efficiently within a single workstation environment, maximizing resource utilization without distributed overhead.
- **Memory & Compute Optimization:** Maintain data in RAM/cache whenever possible for ultra-fast retrieval and processing.
- **GPU-Accelerated Inference:** Run AI workloads natively on RTX A6000 GPUs using vLLM for maximum throughput.
- **Self-Optimization:** Dynamically allocate resources based on workload, historical trends, and system telemetry.
- **Accurate, Multi-Hop Answers:** By coupling a local LLM with a knowledge graph and advanced retrieval methods, HADES reasons over multiple connected facts to produce coherent answers.
- **Fact Verification:** Every LLM-generated response is checked against the knowledge graph to reduce misinformation.
- **Self-Tuning Knowledge:** `.hades` directories as knowledge silos provide localized context while continuously updating embeddings.
- **Version-Controlled Knowledge:** A differential versioning system enables tracking knowledge evolution and efficient incremental updates.
- **System Resource Awareness:** Monitor hardware telemetry to predict resource constraints and optimize accordingly.
- **Autonomic Control:** Manage system processes dynamically based on priority and resource availability.
- **Contextual Awareness:** Provide hierarchical context for queries based on filesystem location.
- **Impact Analysis:** Predict 2nd and 3rd-order effects of knowledge changes through graph relationships.

## 2. Academic Research Foundation

HADES' design and implementation draw from the following cutting-edge research:

1. **PathRAG**  
   *Pruning Graph-based Retrieval Augmented Generation with Relational Paths*  
   [https://arxiv.org/html/2502.14902v1](https://arxiv.org/html/2502.14902v1)  
   Demonstrates path-based retrieval for more coherent reasoning and reduced noise.

2. **Triple Context Restoration (TCR)**  
   *How to Mitigate Information Loss in Knowledge Graphs for GraphRAG: Leveraging Triple Context Restoration and Query-Driven Feedback*  
   [https://arxiv.org/html/2501.15378v1](https://arxiv.org/html/2501.15378v1)  
   Focuses on restoring natural language context around graph triples to improve retrieval quality.

3. **GraphCheck**  
   *GraphCheck: Breaking Long-Term Text Barriers with Extracted Knowledge Graph-Powered Fact-Checking*  
   [https://arxiv.org/html/2502.16514v1](https://arxiv.org/html/2502.16514v1)  
   Provides a post-generation fact-verification mechanism via graph neural networks.

4. **External Continual Learning (ECL)**  
   *In-context Continual Learning Assisted by an External Continual Learner*  
   [https://arxiv.org/html/2412.15563v1](https://arxiv.org/html/2412.15563v1)  
   Guides how a separate "external continual learner" can keep the knowledge base up to date without requiring internal model retraining.

5. **Actor-Network Theory (ANT)**  
   *Science in Action: How to Follow Scientists and Engineers Through Society*  
   Provides a theoretical framework for modeling how networks of actors (code, files, dependencies) interact and influence each other, which HADES applies to predict cascading effects of changes.

HADES adapts and integrates these techniques to create a production-ready system that excels in retrieval, verification, and continual learning.

## 3. High-Level System Architecture

HADES organizes its components as a single-system MI with optimized resource usage:

1. **Local Large Language Model (LLM) Execution**  
   - Deployed using vLLM for GPU-accelerated inference on RTX A6000s.
   - Loads model (e.g., Codestral 22B) directly into VRAM (48GB each) for maximum throughput.
   - Offloads non-critical processing to CPU when needed to optimize GPU resources.
   - Maintains model parameters in GPU memory for rapid inference.

2. **Dual Server Architecture**  
   - **API Server (FastAPI)**: Provides a RESTful HTTP interface for general clients and applications.
   - **MCP Server (WebSockets)**: Offers a persistent connection for direct model integration and tool execution.
   - The servers are implemented separately to maintain clear separation of concerns.

3. **Hybrid Knowledge Storage & Retrieval**  
   - **ArangoDB Knowledge Graph Backbone**:
     - Provides structured storage for `.hades` knowledge silos and graph relationships.
     - Implements vector search (HNSW) for embedding retrieval.
     - Handles hierarchical relationships between `.hades` directories.
     - Performs knowledge validation via GraphCheck.
     - Natively installed on Ubuntu Noble (24.04) for optimal performance.
   - **RAM-Based FAISS + ArangoDB Vector Search**:
     - FAISS maintains most frequently used embeddings in RAM for ultra-fast retrieval.
     - ArangoDB provides persistent storage for all embeddings.
     - System falls back to ArangoDB only if FAISS cache misses.
     - Enables near-instantaneous recall of recent knowledge.
   - **PostgreSQL Authentication**:
     - Handles user authentication and authorization using dedicated 'hades' system user/role.
     - Database name 'hades_test' with specific credentials for consistency.

4. **Direct Database Integration**  
   - Removes the need for intermediate layers when accessing databases.
   - Both PostgreSQL and ArangoDB are directly accessible to services, improving performance and transparency.

5. **Retrieval & Enrichment Pipeline**  
   - **PathRAG**: First component to be implemented; provides graph-based path retrieval that identifies coherent paths of knowledge, with optimized graph queries for single-system performance.
   - **Triple Context Restoration (TCR-QF)**: Second component; reconstructs full textual context for each triple and enriches the knowledge graph iteratively based on query-driven feedback.
   - **LLM Analysis with Embedded Model**: Third component; leverages local model inference with a flexible abstraction layer that supports multiple model implementations (initially Ollama). Includes entity extraction, relationship mapping, and knowledge graph enrichment capabilities, with the model serving as the core intelligence for both document processing and query handling.
   - **GraphCheck Fact Verification**: Final component; compares extracted claims against the knowledge graph via a graph neural network (GNN) running on local GPUs.

6. **Self-Tuning External Continual Learner (ECL)**  
   - **Persistent Knowledge Evolution**: Implemented with `.hades` directories as filesystem-based knowledge silos.
   - **Dynamic Embedding Updates**: Automatically detects stale information and re-embeds critical data.
   - **Hierarchical Knowledge Organization**:
     - Root `.hades`: Project-level knowledge
     - Subdirectory `.hades`: Module-specific knowledge
     - Nested `.hades`: Fine-grained contextual knowledge
   - **Knowledge Upload Integration**: Dropping files into `.hades` directories triggers ingestion into ArangoDB.
   - **Auto-Discovery**: Uses filesystem events (via `inotify` on Linux) to detect changes in `.hades` directories.
   - **RAM-Optimized Retrieval**: Keeps frequently accessed embeddings in memory for instant recall.
   - **Version Management**: Tracks file history within each `.hades` directory for temporal context.
   - **User Memory System**: Stores and retrieves user-specific observations and conversation history using a structured directory system.
   - **Entity-Relationship User Memory**: Represents user memories as typed entities with atomic observations and explicit relationships.

7. **Versioning System**  
   - Tracks all changes to the knowledge graph with semantic versioning.
   - Enables querying knowledge as it existed at specific versions or points in time.
   - Generates training data from diffs between versions for incremental model updates.
   - Supports mapping changes to their 2nd and 3rd-order effects via graph traversal.

8. **Data Ingestion Pipeline**  
   - Validates incoming data using Pydantic models with configurable validation levels.
   - Performs preprocessing and normalization to ensure data quality.
   - Supports batch processing for large data volumes with error handling.
   - Auto-discovers `.hades` directories to update knowledge silos.

9. **Security Layer**  
   - Implements Role-Based Access Control (RBAC) with predefined roles and granular permissions.
   - Provides token-based authentication and API key management.
   - Records comprehensive audit logs for security monitoring.
   - Encrypts sensitive data using modern cryptographic methods.

7. **System Resource Awareness & Autonomic Control**  
   - **Hardware Telemetry**: Monitors CPU, GPU, RAM usage and system logs in real-time.
   - **Predictive Resource Allocation**: Uses historical trends to anticipate resource constraints.
   - **Dynamic Workload Management**: Reallocates CPU/GPU/RAM based on demand and priority.
   - **Proactive Optimization**: Pre-loads necessary embeddings into RAM for anticipated queries.
   - **Background Task Scheduling**: Utilizes idle system time for optimization tasks.
   - **Automatic Process Control**: Throttles non-essential processes during high workloads.

## 4. Core Components and Their Interactions

Below is a simplified interaction flow, illustrating how user queries move through HADES:

1. **System Resource Management (Autonomic Layer)**
   - Monitors available GPU memory, RAM, and CPU resources.
   - Allocates resources based on query complexity and system load.
   - Schedules background tasks during periods of low system utilization.

2. **Authentication & Authorization (Security Layer)**  
   - Validates user or API key credentials and permissions using PostgreSQL ('hades' user).
   - Ensures appropriate access levels for the requested operation.

3. **Query Intake (via MCP)**  
   - The MCP server receives an external user query (supports VSCode Cursor & Windsurf integration).
   - The query is validated and passed internally to HADES.
   - The system identifies relevant `.hades` directories based on query context or filesystem location.
   - Resource requirements are estimated to optimize allocation.

4. **Hybrid Vector Retrieval (First Stage)**  
   - The system first checks RAM-resident FAISS indices for relevant embeddings.
   - For cache misses, the query triggers graph-based retrieval in ArangoDB.
   - PathRAG identifies key facts, nodes, and edges forming relevant paths.
   - Path pruning removes low-relevance connections to focus on coherent reasoning chains.
   - Frequently accessed embeddings are cached in RAM for future queries.

4. **TCR Context Enrichment (Second Stage)**  
   - For each triple retrieved by PathRAG, TCR locates and restores the original textual context.
   - Vector search identifies additional relevant passages that might not be explicitly represented in the graph.
   - Missing knowledge is identified via the TCR Query-Driven Feedback mechanism.

6. **Local LLM Response Generation (Third Stage)**  
   - The locally-hosted LLM (via vLLM on RTX A6000 GPUs) synthesizes information.
   - GPU memory is dynamically allocated based on input context size.
   - Model inference is optimized for the available VRAM (48GB per GPU).
   - The LLM composes a response based on combined PathRAG and TCR context.
   - Context from relevant `.hades` directories influences the response generation.

6. **GraphCheck Verification (Final Stage)**  
   - The system extracts claims from the LLM's output and verifies them against the knowledge graph.
   - If inconsistencies are found, the LLM is prompted to revise or is flagged for user review.
   - Verification may be performed against historical versions if necessary.

8. **Self-Tuning ECL Domain Updates**  
   - The ECL continuously monitors interactions with `.hades` directories.
   - New knowledge from queries is used to update domain embeddings incrementally.
   - Changes to `.hades` directories trigger automatic reindexing of affected knowledge silos.
   - Stale information is automatically detected and re-embedded during system idle time.
   - Background optimization tasks adjust embedding quality based on usage patterns.

9. **Resource-Aware Version Tracking & Impact Analysis**  
   - Changes to the knowledge graph are recorded with version metadata.
   - Impact analysis is scheduled during periods of low system usage.
   - System predicts resource requirements for large-scale analysis operations.
   - For code or document changes, the system pre-allocates resources based on anticipated needs., the system can predict 2nd and 3rd-order effects by traversing dependency edges in the graph.

9. **Final Answer Delivery**  
   - Once validated, the final answer is returned to the user via the MCP interface.

## 5. Technical Design Decisions and Rationale

1. **Dual Server Architecture**  
   - **API Server**: Provides a standardized REST interface for traditional clients (web/mobile apps).
   - **MCP Server**: Creates a specialized WebSocket interface for model integration and efficient tool execution.
   - This separation allows each server to specialize in its specific use case while sharing the same authentication infrastructure.
   - Minimizes overhead by allowing direct calls to database drivers rather than additional intermediate layers.

2. **Ordered Implementation Pipeline**  
   - The implementation follows a logical sequence: PathRAG → TCR → LLM Analysis → GraphCheck.
   - This approach builds each component on a validated foundation, reducing cascading errors.
   - Initial focus on the MCP server allows early integration with LLMs before completing all components.

3. **`.hades` Directory Structure**  
   - Filesystem-based knowledge silos align with UNIX philosophy ("everything is a file").
   - Provides automatic discovery of domain-specific knowledge based on directory location.
   - Enables hierarchical context awareness:
     - Root `.hades` for project-level knowledge
     - Nested `.hades` for increasingly specific context
   - Facilitates incremental updates to knowledge domains.

4. **Actor-Network Theory Applied to Knowledge**  
   - Treats files, functions, and dependencies as "actors" in a dynamic network.
   - Enables predicting cascading effects of changes through graph relationships.
   - Maps direct (1st-order), indirect (2nd-order), and cascading (3rd-order) dependencies.
   - Supports impact analysis and predictive maintenance.

5. **Graph-Based Retrieval**  
   - A graph model (ArangoDB) is more flexible for multi-hop queries than a traditional relational or flat search index.
   - PathRAG's pruning mechanism strikes a balance between retrieval depth and noise reduction.
   - Enables tracking relationships between `.hades` knowledge silos.

6. **Continual Learning as an External Module**  
   - ECL can be updated independently of the core LLM, avoiding costly re-training.
   - Each `.hades` directory acts as a localized knowledge node that can be updated independently.
   - Processes version diffs for efficient incremental updates.

7. **Post-Generation Verification**  
   - Real-time verification of LLM outputs addresses the "hallucination" problem and bolsters factual correctness.
   - GraphCheck's GNN approach effectively leverages local graph neighborhoods to verify discrete claims.
   - Final stage in the pipeline ensures factual accuracy before delivering responses.

8. **Database Strategy**  
   - **PostgreSQL for Authentication**: Provides robust security and user management with minimal overhead.
   - **ArangoDB for Knowledge Graph**: Optimized for graph operations and multi-hop queries.
   - **Direct Database Coupling**: Reduces latency by bypassing conventional HTTP service layers.
   - **Real Database Connections**: Uses actual database connections rather than mocks for more realistic testing and operation.
   - **Native Bare Metal Installation**: All components are installed directly on the system for maximum performance, including ArangoDB configured specifically for Ubuntu Noble (24.04).

6. **Differential Versioning System**  
   - Enables tracking knowledge graph evolution over time without excessive storage overhead.
   - Supports time-travel queries for exploring how knowledge has changed.
   - Facilitates incremental training data generation from changes.
   - Integrated with the password rotation system to ensure secure credential management across all components.

7. **Layered Security Architecture**  
   - RBAC provides fine-grained control appropriate for different user types.
   - Modern encryption and key derivation secure sensitive data.
   - Comprehensive audit logging enables security monitoring and analysis.

8. **Validation-First Data Ingestion**  
   - Strong validation guarantees data quality and consistency at the source.
   - Configurable validation levels (strict, medium, lenient) allow flexibility based on use case.
   - Batch processing with error handling improves efficiency for large data volumes.

## References

HADES architecture and its features rely on the following academic and technical references, also cited throughout the system design:

- **PathRAG**: [Pruning Graph-based RAG with Relational Paths](https://arxiv.org/html/2502.14902v1)  
- **Triple Context Restoration (TCR)**: [How to Mitigate Information Loss in Knowledge Graphs for GraphRAG](https://arxiv.org/html/2501.15378v1)  
- **GraphCheck**: [Breaking Long-Term Text Barriers with Knowledge Graph-Powered Fact-Checking](https://arxiv.org/html/2502.16514v1)  
- **External Continual Learning (ECL)**: [In-context Continual Learning Assisted by an External Continual Learner](https://arxiv.org/html/2412.15563v1)  
- **Model Context Protocol (MCP)**: [https://modelcontextprotocol.io](https://modelcontextprotocol.io)