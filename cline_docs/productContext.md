# Product Context

## Why This Project Exists

HADES (Heuristic Adaptive Data Extrapolation System) is designed to merge a Large Language Model (LLM) with a graph-based knowledge repository, enabling natural language queries to be answered with contextually rich and factually verified responses. By integrating multiple research innovations—PathRAG, Triple Context Restoration (TCR), GraphCheck, and an External Continual Learner (ECL)—into a cohesive pipeline, HADES can efficiently retrieve, verify, and enrich knowledge on-the-fly.

## What Problems It Solves

1. **Multi-Hop Reasoning:**
   - Traditional LLMs often struggle with multi-hop reasoning, where answers require connecting multiple pieces of information spread across different parts of the knowledge base.
   - HADES addresses this by using graph-based retrieval methods to identify coherent paths of knowledge.

2. **Fact Verification:**
   - LLM-generated responses can sometimes contain inaccuracies or "hallucinations."
   - HADES ensures that every response is verified against a knowledge graph, reducing misinformation and increasing reliability.

3. **Continual Learning:**
   - Knowledge bases need to be updated continuously as new information becomes available.
   - HADES incorporates an external continual learner (ECL) to keep the knowledge base fresh without requiring internal model retraining.

4. **Version Control:**
   - Tracking changes in a knowledge graph is crucial for understanding how knowledge evolves over time.
   - HADES maintains a comprehensive versioning system, enabling historical queries and incremental updates.

5. **Data Validation:**
   - Ensuring data quality is essential for maintaining the integrity of the knowledge base.
   - HADES includes robust validation mechanisms to ensure that all ingested data meets predefined standards.

6. **Security:**
   - Protecting sensitive information and ensuring secure access to the system are critical.
   - HADES implements role-based access control (RBAC) and token-based authentication to safeguard against unauthorized access.

## How It Should Work

1. **Query Processing:**
   - Users submit natural language queries through a RESTful API.
   - The query is processed through the following pipeline:
     1. **PathRAG Retrieval:** Identifies relevant paths in the knowledge graph using graph-based retrieval methods.
     2. **Triple Context Restoration (TCR-QF):** Enriches the retrieved paths with contextual information based on query-driven feedback.
     3. **GraphCheck Verification:** Verifies the facts in the generated response against the knowledge graph via a GNN.
     4. **External Continual Learner (ECL):** Updates domain embeddings and suggests any newly ingested relevant information.

2. **Data Ingestion:**
   - New data points can be ingested into the knowledge graph through a secure API endpoint.
   - The ingestion process includes validation, preprocessing, and normalization to ensure data quality.

3. **Version Management:**
   - Users can query historical states of the knowledge graph using version-aware queries.
   - The system maintains detailed change logs for each version, enabling time-travel queries and incremental updates.

4. **Security:**
   - All API endpoints require authentication and authorization.
   - Role-based access control ensures that users have appropriate permissions based on their roles (e.g., admin, editor, analyst, reader).

5. **Monitoring and Logging:**
   - Comprehensive logging is implemented to track important events, warnings, and errors.
   - Monitoring tools like `psutil` are used to identify resource usage and potential bottlenecks.

6. **Deployment:**
   - The system can be containerized using Docker or Docker Compose for easy deployment in various environments.
   - It can be run behind a reverse proxy like Nginx or Caddy for production setups.
   - Process management is handled by `systemd` or `supervisor`.

7. **Documentation:**
   - All components and processes are thoroughly documented using Google-style docstrings.
   - Comprehensive documentation ensures that the system remains maintainable and understandable.

8. **Testing:**
   - Unit tests cover all methods to ensure high test coverage (90% or higher).
   - Both common cases and edge cases are tested to ensure robustness.
