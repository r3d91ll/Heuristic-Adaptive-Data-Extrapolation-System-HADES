# API vs MCP in HADES Architecture

## Overview

HADES implements two distinct server components that serve different purposes:

1. **API Server**: A traditional REST API built with FastAPI
2. **MCP Server**: A WebSocket-based Model Context Protocol (MCP) server

This document explains the differences, use cases, and how they interact within the HADES architecture.

## API Server

The API Server provides a standard REST interface for general clients to interact with HADES.

### Characteristics

- **Technology**: Built with FastAPI
- **Protocol**: HTTP/REST
- **Location**: `src/api/server.py`
- **Purpose**: Serves as the interface for standard applications, web UIs, and third-party integrations
- **Authentication**: JWT-based authentication

### Endpoints

- `/api/authenticate`: User authentication
- `/api/authorize`: Authorization check
- `/api/ingest`: Data ingestion into the knowledge graph
- `/api/query`: Process natural language queries
- `/api/execute_pathrag`: Execute PathRAG operations

### Use Cases

- Web applications connecting to HADES
- Mobile apps requiring HADES functionality
- Third-party integrations with other services
- Administrative operations

## MCP Server

The Model Context Protocol (MCP) server is a specialized interface designed for direct model integration and tool execution.

### Characteristics

- **Technology**: Built with WebSockets
- **Protocol**: WebSocket-based JSON messages
- **Location**: `src/mcp/server.py`
- **Purpose**: Provides a direct connection channel for models (like LLMs) to execute tools and access databases
- **Authentication**: Session-based WebSocket authentication

### Tools

- `show_databases`: Lists all available PostgreSQL and ArangoDB databases
- (Additional tools to be implemented in Phase 3)

### Use Cases

- Direct LLM integration for tool usage
- Database operations that require persistent connections
- Real-time data streaming and updates
- Tool registration and execution

## Key Differences

| Feature | API Server | MCP Server |
|---------|------------|------------|
| Protocol | HTTP/REST | WebSockets |
| Connection | Stateless requests | Persistent connection |
| Primary Client | Applications | Models (LLMs) |
| Message Format | REST with JSON | JSON messages |
| Authentication | JWT per request | Session-based |
| Use Case | General purpose | Model integration & tools |

## Implementation and Testing

Since this architecture supports real database connections rather than mocks (aligned with our development philosophy), both servers can interact with:

- **PostgreSQL**: For structured data and authentication
- **ArangoDB**: For graph-based knowledge storage

## Future Development

As per the development roadmap, the MCP server capabilities will be expanded in Phase 3 to include more tools for data ingestion, queries, and database management.
