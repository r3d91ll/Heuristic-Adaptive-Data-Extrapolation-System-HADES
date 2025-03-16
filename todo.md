# HADES Development TODO

## Phase 1: Deconflict FastAPI and MCP Implementations

### 1. Rename and Reorganize FastAPI Server
- [ ] Create new `src/api` directory
- [ ] Move `src/mcp/server.py` to `src/api/server.py`
- [ ] Move `src/mcp/models.py` to `src/api/models.py`
- [ ] Update imports and references in all affected files
- [ ] Update configuration and environment variables

### 2. Update Documentation
- [ ] Update README.md to clarify the distinction between API and MCP
- [ ] Add documentation about the API server's purpose and endpoints
- [ ] Document the relationship between API and MCP servers

## Phase 2: Implement MCP Server (Core)

### 1. Basic MCP Server Setup
- [ ] Create new MCP server implementation in `src/mcp/server.py`
- [ ] Implement MCP protocol transport layer (HTTP/WebSockets)
- [ ] Implement basic message handling
- [ ] Create configuration for MCP server

### 2. First MCP Tool: Show All Databases
- [ ] Implement tool registration mechanism
- [ ] Create "show_databases" tool that lists all databases
- [ ] Add authentication/authorization for MCP tools
- [ ] Test the tool with an MCP client

### 3. Create Database Reset Script
- [ ] Create `scripts/reset_databases.sh` to wipe all databases
- [ ] Ensure script handles both PostgreSQL and ArangoDB
- [ ] Add safety checks to prevent accidental data loss
- [ ] Test script functionality

## Phase 3: Expand MCP Capabilities

### 1. Data Ingestion Tools
- [ ] Implement "ingest_data" tool for adding data to knowledge graph
- [ ] Add validation and error handling
- [ ] Create test cases for data ingestion
- [ ] Document the data format and requirements

### 2. Query Tools
- [ ] Implement "query" tool for natural language queries
- [ ] Connect to existing orchestrator
- [ ] Add result formatting options
- [ ] Test with various query types

### 3. Database Management Tools
- [ ] Add tools for database backup/restore
- [ ] Implement tools for schema updates
- [ ] Create tools for database statistics and monitoring
- [ ] Test all database operations

## Phase 4: Data Population

### 1. ArangoDB Documentation Ingestion
- [ ] Create parser/scraper for ArangoDB documentation
- [ ] Transform documentation into knowledge graph format
- [ ] Ingest documentation using MCP tools
- [ ] Verify data integrity

### 2. Research Papers Ingestion
- [ ] Identify relevant research papers
- [ ] Extract key information and relationships
- [ ] Transform into knowledge graph format
- [ ] Ingest using MCP tools

### 3. HADES Codebase Ingestion
- [ ] Analyze codebase structure
- [ ] Extract module relationships and dependencies
- [ ] Transform into knowledge graph format
- [ ] Ingest using MCP tools

## Phase 5: Testing and Validation

### 1. Unit Tests
- [ ] Create unit tests for all MCP components
- [ ] Test error handling and edge cases
- [ ] Ensure test coverage for critical functionality

### 2. Integration Tests
- [ ] Create end-to-end tests for MCP server
- [ ] Test interaction with databases
- [ ] Verify data integrity across operations

### 3. Performance Testing
- [ ] Benchmark MCP server performance
- [ ] Identify and address bottlenecks
- [ ] Test with large datasets

## Phase 6: Documentation and Cleanup

### 1. User Documentation
- [ ] Create comprehensive user guide
- [ ] Document all available MCP tools
- [ ] Provide examples and tutorials

### 2. Developer Documentation
- [ ] Document architecture and design decisions
- [ ] Create API reference
- [ ] Add code comments and docstrings

### 3. Final Cleanup
- [ ] Remove deprecated code
- [ ] Standardize naming conventions
- [ ] Ensure consistent error handling
