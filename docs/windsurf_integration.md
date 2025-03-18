# HADES Windsurf Integration Guide

This comprehensive guide explains how to set up and use the HADES MCP server with Windsurf (Codeium) for AI-augmented knowledge graph capabilities.

## Overview

HADES exposes its tools via the Model Context Protocol (MCP), which allows large language models like those in Windsurf/Codeium to interact with the HADES knowledge graph directly. The server supports the MCP protocol version 2024-11-05.

Additionally, HADES features an embedded model architecture with a flexible abstraction layer that supports multiple model implementations (initially Ollama). This architecture provides intelligent entity extraction and relationship mapping capabilities for knowledge graph construction. For more details, see the [implementation plan](../HADES_Embedded_Model_Implementation_Plan.md).

This integration enables Windsurf to:

1. Ingest data directly into the HADES knowledge graph
2. Retrieve paths from the knowledge graph based on natural language queries
3. Get information about the connected databases
4. Leverage embedded model capabilities for enhanced knowledge processing

## Configuration

### MCP Server Configuration

The HADES MCP server now supports the stdio transport type, which is required by Windsurf. 

For Windsurf integration, the server needs to be started with the `--stdio` flag:

```bash
python -m src.mcp.server --stdio
```

### Windsurf Configuration

To configure Windsurf to use the HADES MCP server:

1. Create or edit the Windsurf MCP configuration file at `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "hades": {
      "command": "/path/to/Heuristic-Adaptive-Data-Extrapolation-System-HADES/.venv/bin/python",
      "args": [
        "-m",
        "src.mcp.server",
        "--stdio"
      ],
      "cwd": "/path/to/Heuristic-Adaptive-Data-Extrapolation-System-HADES",
      "env": {
        "PYTHONPATH": "/path/to/Heuristic-Adaptive-Data-Extrapolation-System-HADES"
      }
    }
  }
}
```

2. Ensure the PYTHONPATH environment variable points to your HADES repository root directory

### Environment Variables

The MCP server will load environment variables from the `.env` file in the HADES root directory. Make sure this file includes the necessary database credentials and configuration:

```
# PostgreSQL connection settings
HADES_PG_HOST=localhost
HADES_PG_PORT=5432
HADES_PG_USER=your_pg_user
HADES_PG_PASSWORD=your_pg_password

# ArangoDB connection settings
HADES_ARANGO_URL=http://localhost:8529
HADES_ARANGO_USER=your_arango_user
HADES_ARANGO_PASSWORD=your_arango_password

# HADES authentication
HADES_SERVICE_API_KEY=your_api_key
```

3. Restart Windsurf or refresh the MCP configuration.

## Available Tools

The HADES MCP server exposes the following tools that can be accessed via the `tools/list` and `tools/call` methods as per the MCP specification:

1. **show_databases**: Lists all available PostgreSQL and ArangoDB databases
   - Arguments: None
   - Returns: Object with lists of databases formatted as text content

2. **ingest_data**: Ingests data into the knowledge graph using PathRAG
   - Arguments:
     - `data`: Array of data points to ingest (required)
     - `domain`: Domain to associate with the data (default: "general")
     - `as_of_version`: Optional version to tag the data with
   - Returns: Count of ingested entities and relationships formatted as text content

3. **pathrag_retrieve**: Retrieves paths from the knowledge graph using PathRAG
   - Arguments:
     - `query`: The query to retrieve paths for (required)
     - `max_paths`: Maximum number of paths to retrieve (default: 5)
     - `domain_filter`: Optional domain filter
     - `as_of_version`: Optional version to query against
   - Returns: Array of retrieved paths formatted as text content

## Testing and Verification

### Test Script

A test script is provided to verify the MCP server's stdio transport functionality:

```bash
python src/test_windsurf_mcp.py
```

This script tests:
1. Server initialization with protocol version 2024-11-05
2. Tools listing via the `tools/list` method
3. Tool execution via the `tools/call` method (show_databases)
4. Proper cleanup

This follows the standard MCP protocol for tool discovery and execution.

### Windsurf Integration Testing

After configuring the MCP server, you can verify the integration in Windsurf by:

1. Opening Windsurf (Codeium)
2. Navigating to Settings > MCP Servers
3. You should see "hades" listed as an available server
4. Click "Refresh" if it doesn't appear immediately
5. If you see "Ready" status, the integration is working

You can then have Cascade use HADES tools by asking it questions like:
- "Show me what databases are available in HADES"
- "Use HADES to find information about [topic]"
- "Ingest this data into the HADES knowledge graph: [data]"

## Troubleshooting

### Common Issues

1. **"Error: request failed. Check your configuration"**
   - Verify the Python path in the MCP config is correct
   - Check that the `--stdio` flag is included in the args
   - Ensure the cwd path exists and is readable

2. **Database Connection Errors**
   - Confirm PostgreSQL and ArangoDB are running
   - Verify credentials in .env file
   - Check database user permissions

3. **Missing Tools**
   - Ensure the server starts correctly
   - Check for errors in the MCP server logs

4. **Method not found errors**
   - The HADES MCP server (version 1.0.1+) now properly handles all required MCP protocol methods including:
     - `resources/list`
     - `resources/templates/list`
     - `notifications/initialized`
   - If you see `Method not found` errors in the logs, ensure you're using the latest version of the server

### Debugging

To debug the MCP server, run it manually with the `--stdio` flag and watch for error messages:

```bash
python -m src.mcp.server --stdio
```

You can also check the server's output logs in the Windsurf developer tools console.

## Advanced Configuration

### Custom Tool Development

The MCP server can be extended with custom tools by adding new handlers to the `tools` dictionary in the `MCPServer` class initialization.

## Security Considerations

- The API key in the `.env` file should be kept secure
- Database credentials should use limited-privilege accounts
- Consider using environment variables instead of editing the `.env` file directly

For more detailed information about the MCP implementation, see the `src/mcp/server.py` file.
