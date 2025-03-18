# Documentation Ingestion Guide for HADES

This guide explains how to ingest documentation into the HADES knowledge graph for semantic search and retrieval.

## Overview

HADES provides powerful tools for ingesting documentation from various sources, including:

- HTML webpages
- Markdown files
- Crawling entire documentation sites

The ingestion process involves three main steps:

1. **Conversion**: Convert documentation from its source format to markdown
2. **Preparation**: Process the markdown files to prepare them for ingestion
3. **Ingestion**: Add the prepared documents to the HADES knowledge graph

## Installation Requirements

Ensure you have the required dependencies installed:

```bash
cd /path/to/HADES
source .venv/bin/activate
pip install requests beautifulsoup4 markdownify
```

## Using the Ingestion Tools

HADES provides two main scripts for handling documentation ingestion:

- `hades_ingest.py`: A comprehensive tool for converting, preparing, and ingesting documentation
- `test_arango_docs.py`: A tool for testing retrieval of ingested documentation

### Single Page Conversion

To convert a single webpage to markdown:

```bash
python src/hades_ingest.py convert-url https://docs.arangodb.com/stable/python-client/ --output docs/arango-python.md
```

### Site Crawling

To crawl and convert an entire documentation site:

```bash
python src/hades_ingest.py crawl https://docs.arangodb.com/stable/python-client/ --output-dir data/markdownified/python-arango --max-pages 50 --domain python-arango-docs
```

### Preparing Documents for Ingestion

To prepare markdown files for ingestion:

```bash
python src/hades_ingest.py prepare data/markdownified/python-arango --output data/markdownified/python-arango-ingest.json --domain python-arango-docs
```

### Ingesting Documents

To ingest prepared documents into HADES:

```bash
python src/hades_ingest.py ingest data/markdownified/python-arango-ingest.json --domain python-arango-docs --batch-size 5
```

### All-in-One Operation

To perform all steps (crawl, prepare, and ingest) in one command:

```bash
python src/hades_ingest.py all https://docs.arangodb.com/stable/python-client/ --output-dir data/markdownified/python-arango --max-pages 50 --domain python-arango-docs --batch-size 5
```

## Integration with Windsurf

When using HADES with Windsurf, you can use the MCP tools directly:

### Ingesting Documents

Use the `ingest_data` tool with the following parameters:
- `data`: An array of document objects to ingest
- `domain`: The domain to associate with the documents (e.g., "python-arango-docs")

Example:
```
ingest_data:
  data: [{"id": "collection_md", "title": "Collection", "content": "# Collections\n\nA collection contains documents...", "metadata": {"type": "documentation", "domain": "python-arango-docs", "path": "collection.md"}}]
  domain: python-arango-docs
```

### Retrieving Documents

Use the `pathrag_retrieve` tool with the following parameters:
- `query`: The natural language query to search for
- `domain_filter`: The domain to search within (e.g., "python-arango-docs")
- `max_paths`: The maximum number of results to return

Example:
```
pathrag_retrieve:
  query: How to create a collection in ArangoDB using Python?
  domain_filter: python-arango-docs
  max_paths: 5
```

## Testing Retrieval

To test if your documentation was ingested correctly:

```bash
python src/test_arango_docs.py --query "How to create a collection in ArangoDB?" --domain python-arango-docs
```

## Supported Document Structure

When preparing documents for ingestion, they should have the following structure:

```json
{
  "id": "unique_document_id",
  "title": "Document Title",
  "content": "The full markdown content of the document",
  "source": "Original source of the document (URL or file path)",
  "metadata": {
    "type": "documentation",
    "domain": "domain-name",
    "path": "relative/path/to/document.md",
    "any_other_metadata": "value"
  }
}
```

## Best Practices

1. **Domain Naming**: Use consistent domain names (e.g., "python-arango-docs") for related documentation
2. **Batch Size**: Keep batch sizes reasonable (5-10 documents) to avoid timeouts
3. **Content Quality**: Ensure markdown content is well-formed and free of HTML artifacts
4. **Testing**: Always test retrieval after ingestion to verify document accessibility
5. **Versioning**: Consider including version information in the domain name for versioned documentation (e.g., "python-arango-docs-v3.9")
