# ArangoDB Documentation Integration with HADES

This document outlines how ArangoDB Python documentation has been integrated into the HADES knowledge graph, and how to utilize this documentation in your projects.

## Overview

ArangoDB Python driver documentation has been fully ingested into the HADES knowledge graph, providing:

- Semantic search and retrieval of ArangoDB Python client documentation
- Natural language queries for finding specific operations
- Context-aware answers to ArangoDB usage questions

## Ingested Documentation Sections

The following sections of the ArangoDB Python documentation have been successfully ingested:

1. **Overview**: General introduction to the Python driver
2. **Collections**: Working with collections in ArangoDB
3. **Indexes**: Creating and managing indexes for optimized queries
4. **Graphs**: Graph operations, vertices, and edges
5. **Simple Queries**: Basic querying operations
6. **AQL**: Advanced Query Language implementation
7. **Pregel**: Graph analytics engine
8. **Foxx**: JavaScript-based microservices in ArangoDB
9. **Replication**: Data replication between ArangoDB instances
10. **Transactions**: Transaction processing and guarantees
11. **Clusters**: Working with distributed ArangoDB clusters
12. **Analyzers**: Text analysis capabilities for search

## Querying the Documentation

### Using Windsurf

Use the following MCP tool in Windsurf to query the ArangoDB documentation:

```
mcp0_pathrag_retrieve:
  query: How to create a collection in ArangoDB using Python?
  domain_filter: python-arango-docs
  max_paths: 3
```

### Using Python

For programmatic access, use the provided demo script:

```bash
cd /home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES
source .venv/bin/activate
python src/examples/arango_docs_demo.py
```

The demo script shows three different ways to access the documentation:
1. Direct API access (if available)
2. Windsurf command format
3. Command-line interface commands

### Example Queries

Here are some example queries you can try:

- "How to create a collection in ArangoDB using Python?"
- "How to execute an AQL query in Python?"
- "What is a graph in ArangoDB?"
- "How to create indexes in ArangoDB using Python?"
- "How to perform transactions in ArangoDB?"

## Updating the Documentation

If you need to update the documentation (e.g., for a new version of ArangoDB):

1. Use the `hades_ingest.py` script to crawl the updated documentation:

```bash
python src/hades_ingest.py crawl https://docs.arangodb.com/stable/python-client/ \
  --output-dir data/markdownified/python-arango-new \
  --max-pages 100 \
  --domain python-arango-docs-new
```

2. Prepare the documentation for ingestion:

```bash
python src/hades_ingest.py prepare data/markdownified/python-arango-new \
  --output data/markdownified/python-arango-new-ingest.json \
  --domain python-arango-docs-new
```

3. Ingest the updated documentation:

```bash
python src/hades_ingest.py ingest data/markdownified/python-arango-new-ingest.json \
  --domain python-arango-docs-new \
  --batch-size 5
```

Alternatively, use the all-in-one command:

```bash
python src/hades_ingest.py all https://docs.arangodb.com/stable/python-client/ \
  --output-dir data/markdownified/python-arango-new \
  --max-pages 100 \
  --domain python-arango-docs-new \
  --batch-size 5
```

## Troubleshooting

If you encounter issues with the documentation:

1. **Empty query results**: Ensure you're using the correct domain filter (`python-arango-docs`)
2. **Connectivity errors**: Verify the HADES MCP server is running
3. **Ingestion failures**: Check batch sizes and document formatting
4. **Windsurf integration**: Verify the MCP configuration in `~/.codeium/windsurf/mcp_config.json`

## Further Development

Potential improvements for the ArangoDB documentation integration:

1. Add versioned documentation support
2. Create a specialized ArangoDB query assistant
3. Integrate code examples with executable test capabilities
4. Add automatic documentation update capabilities

## Related Documentation

For more information, see the following resources:

- [Documentation Ingestion Guide](documentation_ingestion.md)
- [Windsurf Integration Guide](windsurf_integration.md)
- [ArangoDB Python Documentation](https://docs.arangodb.com/stable/python-client/)
