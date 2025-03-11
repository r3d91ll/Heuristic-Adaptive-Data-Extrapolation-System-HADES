# System Patterns

## How the System is Built

HADES (Heuristic Adaptive Data Extrapolation System) is built as a modular system with clear separation of concerns:

1. **Core Components:**
   - **Large Language Model (LLM):** Handles query interpretation and response generation.
   - **Knowledge Graph Database (ArangoDB):** Stores facts, documents, and relationships in a graph structure.
   - **Direct Database Integration (via MCP):** Removes the need for an HTTP API layer, reducing latency and boosting transparency in debugging.

2. **Retrieval & Enrichment:**
   - **PathRAG:** Graph-based path retrieval that identifies coherent paths of knowledge.
   - **Triple Context Restoration (TCR-QF):** Reconstructs full textual context for each triple based on query-driven feedback.
   - **External Continual Learner (ECL):** Maintains and updates domain embeddings to preserve relevance over time.

3. **GraphCheck Fact Verification:**
   - Post-generation step that compares extracted claims against the knowledge graph via a graph neural network (GNN).
   - Initiates a feedback loop if facts are incorrect or incomplete.

4. **Versioning System:**
   - Tracks all changes to the knowledge graph with semantic versioning.
   - Enables querying historical states of the knowledge graph.

5. **Data Ingestion Pipeline:**
   - Validates incoming data using Pydantic models.
   - Performs preprocessing and normalization to ensure data quality.
   - Supports batch processing for large data volumes with error handling.

6. **Security Layer:**
   - Implements Role-Based Access Control (RBAC) with predefined roles and permissions.
   - Provides token-based authentication and API key management.
   - Records comprehensive audit logs for security monitoring and analysis.

## Key Technical Decisions

1. **Graph Database Choice:**
   - Chose ArangoDB for its efficient graph traversal capabilities and support for multi-model data storage.

2. **NLP Model Selection:**
   - Used `ModernBERT-large` for better entity recognition and relationship extraction.
   - Employed BERT-based models for generating embeddings and verifying claims.

3. **Version Control Strategy:**
   - Implemented semantic versioning to track changes in the knowledge graph, ensuring historical queries can be accurately reproduced.

4. **Security Implementation:**
   - Utilized JWT tokens for authentication and authorization.
   - Designed RBAC with predefined roles and permissions to ensure secure access control.

5. **Data Pipeline Management:**
   - Used Pydantic models for data validation and preprocessing.
   - Employed scripts or tools like `dvc` to manage data preprocessing and ensure reproducibility.

6. **Experiment Tracking:**
   - Maintained comprehensive logs of experiments, including parameters, results, and environmental details.
   - Utilized `mlflow` and `tensorboard` for experiment tracking (optional).

## Architecture Patterns

1. **Modular Design:**
   - Each module has a well-defined single responsibility.
   - Favored composition over inheritance to promote reusability and maintainability.

2. **RESTful API Design:**
   - Defined clear and RESTful API routes using FastAPI's `APIRouter`.
   - Used Pydantic models for rigorous request and response data validation.
   - Configured Cross-Origin Resource Sharing (CORS) settings correctly.

3. **Database Best Practices:**
   - Designed database schemas efficiently, optimized queries, and used indexes wisely.
   - Ensured proper release of unused resources to prevent memory leaks.

4. **Security Patterns:**
   - Implemented robust authentication and authorization mechanisms using JWT tokens and RBAC.
   - Recorded comprehensive audit logs for security monitoring and analysis.

5. **Performance Optimization:**
   - Leverage `async` and `await` for I/O-bound operations to maximize concurrency.
   - Applied caching where appropriate to improve performance.
   - Monitored resource usage and identified bottlenecks using tools like `psutil`.

6. **Testing Patterns:**
   - Aimed for high test coverage (90% or higher) using `pytest`.
   - Tested both common cases and edge cases.
   - Used specific exception types, provided informative error messages, and handled exceptions gracefully.

7. **Documentation Patterns:**
   - Provided clear, Google-style docstrings for all functions, methods, and classes.
   - Included usage examples where helpful.
   - Ensured that all documentation is up-to-date and follows best practices.
