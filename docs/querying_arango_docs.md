# Querying ArangoDB Documentation with HADES

This tutorial walks you through the process of querying the ingested ArangoDB documentation using the HADES knowledge graph.

## Prerequisites

- HADES project set up and running
- Windsurf IDE with MCP integration configured
- ArangoDB documentation already ingested into HADES (domain: `python-arango-docs`)

## Using Windsurf to Query Documentation

### Step 1: Open Windsurf IDE

Launch Windsurf and ensure that the HADES MCP integration is configured properly in `~/.codeium/windsurf/mcp_config.json`.

### Step 2: Use the MCP Tool for Retrieval

In Windsurf, use the following MCP tool to retrieve information:

```
mcp0_pathrag_retrieve:
  query: How to create a collection in ArangoDB using Python?
  domain_filter: python-arango-docs
  max_paths: 3
```

This will retrieve up to 3 paths from the knowledge graph that are relevant to creating collections in ArangoDB using Python.

### Step 3: Analyze the Results

The results will include:
- Relevant document paths from the knowledge graph
- Content excerpts that match your query
- Confidence scores for each result

### Example Queries

Here are some example queries to try:

#### Basic Collection Operations

```
mcp0_pathrag_retrieve:
  query: How to create a collection in ArangoDB using Python?
  domain_filter: python-arango-docs
  max_paths: 3
```

#### Executing AQL Queries

```
mcp0_pathrag_retrieve:
  query: How to execute an AQL query in Python?
  domain_filter: python-arango-docs
  max_paths: 3
```

#### Working with Graphs

```
mcp0_pathrag_retrieve:
  query: How to create a graph in ArangoDB using Python?
  domain_filter: python-arango-docs
  max_paths: 3
```

#### Creating Indexes

```
mcp0_pathrag_retrieve:
  query: How to create a hash index in ArangoDB?
  domain_filter: python-arango-docs
  max_paths: 3
```

#### Transactions

```
mcp0_pathrag_retrieve:
  query: How to use transactions in ArangoDB with Python?
  domain_filter: python-arango-docs
  max_paths: 3
```

## Using the Command Line Interface

If you prefer using the command line, you can use the provided test script:

```bash
cd /home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES
source .venv/bin/activate
python src/test_arango_docs.py --query "How to create a collection in ArangoDB using Python?" --domain python-arango-docs
```

## Using the Python Demo Script

For a comprehensive demonstration of different query methods:

```bash
cd /home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES
source .venv/bin/activate
python src/examples/arango_docs_demo.py
```

## Advanced Usage: Combining Multiple Queries

For more complex information needs, you can combine multiple queries:

1. First, get an overview of collections:
```
mcp0_pathrag_retrieve:
  query: What are collections in ArangoDB?
  domain_filter: python-arango-docs
  max_paths: 2
```

2. Then, ask about specific operations:
```
mcp0_pathrag_retrieve:
  query: How to add documents to a collection?
  domain_filter: python-arango-docs
  max_paths: 2
```

3. Finally, inquire about advanced features:
```
mcp0_pathrag_retrieve:
  query: How to perform a bulk import of documents?
  domain_filter: python-arango-docs
  max_paths: 2
```

## Tips for Better Queries

1. **Be specific**: Specific queries like "How to create a named graph in ArangoDB" work better than vague ones like "How to use graphs"

2. **Include context**: Mentioning "Python" or "python-arango" helps target the right documentation

3. **Use technical terms**: Including ArangoDB-specific terminology (collection, document, AQL, etc.) improves results

4. **Limit scope**: Focus on one operation or concept per query for the best results

## Troubleshooting

- If results are empty, try rephrasing your query or broadening it slightly
- If the results aren't relevant, try adding more specific technical terms 
- If you're getting errors, ensure the HADES MCP server is running correctly
- Check that you're using the correct domain filter (`python-arango-docs`)

## Next Steps

- Explore the [Documentation Ingestion Guide](documentation_ingestion.md) to understand how documents are processed
- Read the [ArangoDB Integration Guide](arango_integration.md) for a comprehensive overview
- Check the [Windsurf Integration Guide](windsurf_integration.md) for MCP configuration details
