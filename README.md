# HADES - Hybrid Architecture for Dynamic Enrichment System

HADES is a system that integrates a Large Language Model (LLM) with a graph-based knowledge repository, enabling contextually rich and factually verified responses to natural language queries. It combines several research innovations into a cohesive pipeline:

- **PathRAG**: Graph-based path retrieval with relational pruning
- **Triple Context Restoration (TCR)**: Restores natural language context around graph triples
- **GraphCheck**: Post-generation fact verification mechanism
- **External Continual Learner (ECL)**: Keeps knowledge base up-to-date without model retraining

## Architecture Overview

HADES organizes its components as a modular pipeline:

1. **Large Language Model (LLM)**: Primary interface for interpreting queries and generating responses
2. **Knowledge Graph Database (ArangoDB)**: Stores facts, documents, and relationships in a graph structure
3. **Direct Database Integration (via MCP)**: Allows direct queries to ArangoDB
4. **Retrieval & Enrichment**: PathRAG, TCR, and ECL components
5. **GraphCheck Fact Verification**: Compares extracted claims against the knowledge graph

## Installation

### Prerequisites

- Python 3.9+
- ArangoDB 3.8+
- Poetry for dependency management

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

# Run database setup
poetry run python -m src.db.setup
```

## Development

HADES development follows a phased approach:

1. **Phase 1**: Core Architecture & Basic Retrieval
2. **Phase 2**: Advanced Retrieval & TCR Integration
3. **Phase 3**: Fact-Checking & Continual Learning
4. **Phase 4**: Finalization & Production Readiness

## Running HADES

```bash
# Start the MCP server
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
