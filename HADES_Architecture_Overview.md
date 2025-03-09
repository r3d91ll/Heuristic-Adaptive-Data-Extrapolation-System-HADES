# HADES Architecture Overview

## 1. Introduction and System Purpose

HADES is designed to merge a Large Language Model (LLM) with a graph‐based knowledge repository, enabling natural language queries to be answered with contextually rich and factually verified responses. By integrating multiple research innovations—PathRAG, Triple Context Restoration (TCR), GraphCheck, and an External Continual Learner (ECL)—into a cohesive pipeline, HADES can efficiently retrieve, verify, and enrich knowledge on-the-fly.

### Key Goals and Purpose

- **Accurate, Multi-Hop Answers:** By coupling an LLM with a knowledge graph and advanced retrieval/verification methods, HADES can reason over multiple connected facts to produce coherent multi-hop answers.
- **Fact Verification:** Every LLM-generated response is checked against the knowledge graph to reduce misinformation and increase reliability.
- **Continual Updates:** An external continual learning module (ECL) updates the knowledge representation as new data arrives, ensuring that HADES remains current.
- **Secure Interface:** All external model interactions occur through the Model Context Protocol (MCP), providing a unified interface for standardization and security.
- **Version Control:** A comprehensive differential versioning system enables tracking the evolution of knowledge, time-travel queries, and efficient incremental updates.
- **Data Validation:** Robust validation and preprocessing ensure data quality and consistency throughout the ingestion pipeline.
- **Role-Based Security:** Fine-grained access control with role-based permissions ensures secure and appropriate system access.

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

HADES adapts and integrates these techniques to create a production-ready system that excels in retrieval, verification, and continual learning.

## 3. High-Level System Architecture

HADES organizes its components as a modular pipeline with a layered architecture:

1. **Large Language Model (LLM)**  
   - Serves as the primary interface for interpreting queries and generating responses.
   - Uses augmented knowledge rather than domain-specific fine-tuning.

2. **Knowledge Graph Database (ArangoDB)**  
   - Stores all facts, documents, and relationships in a graph structure.
   - Provides efficient multi-hop queries for advanced reasoning.
   - Integrates version tracking to maintain history of all changes.

3. **Direct Database Integration (via MCP)**  
   - Removes the need for a separate HTTP API layer.
   - The LLM and supporting modules can issue queries directly to ArangoDB, reducing latency and boosting transparency in debugging.

4. **Retrieval & Enrichment**  
   - **PathRAG**: Graph-based path retrieval that identifies coherent paths of knowledge, rather than retrieving disjoint facts. Supports version-aware queries and time-travel.
   - **Triple Context Restoration (TCR-QF)**: Reconstructs full textual context for each triple and enriches the knowledge graph iteratively based on query-driven feedback.
   - **External Continual Learner (ECL)**: Maintains and updates domain embeddings (e.g., using ModernBERT-large) to preserve relevance over time. Processes incremental updates based on version diffs.

5. **GraphCheck Fact Verification**  
   - Post-generation step that compares extracted claims against the knowledge graph via a graph neural network (GNN).
   - Initiates a feedback loop if facts are incorrect or incomplete.
   - Supports version-aware verification to check facts against historical states.

6. **Versioning System**  
   - Tracks all changes to the knowledge graph with semantic versioning.
   - Enables querying knowledge as it existed at specific versions or points in time.
   - Generates training data from diffs between versions for incremental model updates.

7. **Data Ingestion Pipeline**  
   - Validates incoming data using Pydantic models with configurable validation levels.
   - Performs preprocessing and normalization to ensure data quality.
   - Supports batch processing for large data volumes with error handling.

8. **Security Layer**  
   - Implements Role-Based Access Control (RBAC) with predefined roles and granular permissions.
   - Provides token-based authentication and API key management.
   - Records comprehensive audit logs for security monitoring.
   - Encrypts sensitive data using modern cryptographic methods.

## 4. Core Components and Their Interactions

Below is a simplified interaction flow, illustrating how user queries move through HADES:

1. **Authentication & Authorization (Security Layer)**  
   - Validates user or API key credentials and permissions.
   - Ensures appropriate access levels for the requested operation.

2. **Query Intake (via MCP)**  
   - The MCP server receives an external user query.
   - The query is validated and passed internally to HADES.

3. **PathRAG Retrieval**  
   - The query triggers graph-based retrieval in ArangoDB, identifying key facts, nodes, and edges forming relevant paths.
   - If a specific version is requested, retrieval is version-aware.

4. **TCR-QF and ECL**  
   - Missing knowledge is identified (if any) via the LLM's partial response and the TCR Query-Driven Feedback mechanism.
   - ECL updates relevant domain embeddings and suggests any newly ingested information if present.

5. **LLM Response Generation**  
   - The LLM composes an initial response based on retrieved paths and enriched context.

6. **GraphCheck Verification**  
   - The system extracts claims from the LLM's output and verifies them against the knowledge graph.
   - If inconsistencies are found, the LLM is prompted to revise or is flagged for user review.
   - Verification may be performed against historical versions if necessary.

7. **Version Tracking**  
   - Any changes to the knowledge graph are recorded with version metadata.
   - Affected domains are identified for potential ECL updates.

8. **Final Answer Delivery**  
   - Once validated, the final answer is returned to the user via the MCP interface.

## 5. Technical Design Decisions and Rationale

1. **MCP Server Integration**  
   - Ensures all external access is standardized and securely mediated.
   - Minimizes overhead by allowing direct calls to the database driver rather than an extra REST layer.

2. **Graph-Based Retrieval**  
   - A graph model (ArangoDB) is more flexible for multi-hop queries than a traditional relational or flat search index.
   - PathRAG's pruning mechanism strikes a balance between retrieval depth and noise reduction.

3. **Continual Learning as an External Module**  
   - ECL can be updated independently of the core LLM, avoiding costly re-training of the main model while still keeping the knowledge base fresh.
   - Processes version diffs for efficient incremental updates.

4. **Post-Generation Verification**  
   - Real-time verification of LLM outputs addresses the "hallucination" problem and bolsters factual correctness.
   - GraphCheck's GNN approach effectively leverages local graph neighborhoods to verify discrete claims.

5. **Direct Database Coupling**  
   - Reduces latency by bypassing a conventional HTTP service layer.
   - Eases troubleshooting, as both the LLM queries and the database logs can be analyzed in one place.

6. **Differential Versioning System**  
   - Enables tracking knowledge graph evolution over time without excessive storage overhead.
   - Supports time-travel queries for exploring how knowledge has changed.
   - Facilitates incremental training data generation from changes.

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