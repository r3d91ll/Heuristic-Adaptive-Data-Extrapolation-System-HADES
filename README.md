# HADES - Hybrid Architecture for Dynamic Enrichment System

HADES is a system that integrates a Large Language Model (LLM) with a graph-based knowledge repository, enabling contextually rich and factually verified responses to natural language queries. It combines several research innovations into a cohesive pipeline:

- **PathRAG**: Graph-based path retrieval with relational pruning
- **Triple Context Restoration (TCR)**: Restores natural language context around graph triples
- **GraphCheck**: Post-generation fact verification mechanism
- **External Continual Learner (ECL)**: Keeps knowledge base up-to-date without model retraining

## Architecture Overview

HADES organizes its components as a modular pipeline:

1. **Large Language Model (LLM)**: Primary interface for interpreting queries and generating responses
2. **Dual Server Architecture**:
   - **API Server (FastAPI)**: REST API for general client interactions
   - **MCP Server (WebSockets)**: Direct model integration and tool execution
3. **Database Systems**:
   - **PostgreSQL**: Handles user authentication and authorization
   - **ArangoDB**: Stores facts, documents, and relationships in a document, vector, and graph structures
4. **Retrieval & Enrichment**: PathRAG, TCR, and ECL components
5. **GraphCheck Fact Verification**: Compares extracted claims against the knowledge graph

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 14+ (native installation with dedicated 'hades' user) ✓
- ArangoDB 3.8+ (via Docker for Ubuntu Noble 24.04 compatibility) ✓
- Poetry for dependency management
- High-end workstation (optimized for AMD Threadripper 7960X + 256GB RAM + 2x RTX A6000 GPUs)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/hades.git
cd hades

# Install dependencies
poetry install

# Configure environment variables
cp .env.example .env
# Edit .env with your configuration

# Update credentials for system user and database roles if needed
# The 'hades' system user with password 'o$n^3W%QD0HGWxH!' and 'hades_test' database are already set up
sudo scripts/rotate_hades_password.sh

# Initialize databases
scripts/reset_databases.sh
```

## Security and Password Management

HADES includes a password rotation script that:
- Manages the 'hades' system user
- Updates PostgreSQL and ArangoDB authentication
- Generates secure random passwords
- Synchronizes credentials across all components
- Updates environment files with new credentials

To rotate passwords:

```bash
sudo scripts/rotate_hades_password.sh
```

## Development

HADES development follows a clearly defined phased approach:

1. **Phase 1**: Model Context Protocol (MCP) Server Foundation
2. **Phase 2**: PathRAG Implementation
3. **Phase 3**: Triple Context Restoration (TCR) & LLM Integration
4. **Phase 4**: GraphCheck Validation & System Optimization
5. **Phase 5**: Performance Enhancement & Mojo Migration
6. **Phase 6**: Full Autonomous Intelligence

This implementation order (MCP → PathRAG → TCR → LLM Analysis → GraphCheck) ensures each component builds upon a validated foundation, reducing cascading errors. The External Continual Learner (ECL) with `.hades` directories is integrated progressively throughout all phases.

See [HADES_Development_Phases.md](HADES_Development_phases.md) for detailed timeline and [HADES_Implementation_Specification.md](HADES_Implementation_Specification.md) for component details.

## Running HADES

```bash
# Start the API server
poetry run python -m src.api.server

# Start the MCP server (in a separate terminal)
poetry run python -m src.mcp.server

# In a separate terminal, run queries
poetry run python -m src.cli.query "Your natural language query here"
```

## Academic Research Foundation

HADES' design and implementation draw from the following research:

1. **PathRAG**: [Pruning Graph-based RAG with Relational Paths](https://arxiv.org/html/2502.14902v1)
2. **Triple Context Restoration (TCR)**: [How to Mitigate Information Loss in Knowledge Graphs for GraphRAG](https://arxiv.org/html/2501.15378v1)
3. **GraphCheck**: [Breaking Long-Term Text Barriers with Knowledge Graph-Powered Fact-Checking](https://arxiv.org/html/2502.16514v1)
4. **External Continual Learning (ECL)**: [In-context Continual Learning Assisted by an External Continual Learner](https://arxiv.org/html/2412.15563v1)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
