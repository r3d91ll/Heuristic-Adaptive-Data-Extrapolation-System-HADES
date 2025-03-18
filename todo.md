# HADES Development TODO

## Completed Tasks

### Database Setup
- [x] Set up PostgreSQL with dedicated 'hades' system user and 'hades_test' database
- [x] Configure ArangoDB via native installation for Ubuntu Noble (24.04) compatibility
- [x] Create password rotation script (`scripts/rotate_hades_password.sh`) for database credentials
- [x] Configure real database connections for testing rather than using mocks

### Phase 1: Deconflict FastAPI and MCP Implementations

#### 1. Rename and Reorganize FastAPI Server
- [x] Create new `src/api` directory
- [x] Move `src/mcp/server.py` to `src/api/server.py`
- [x] Move `src/mcp/models.py` to `src/api/models.py`
- [x] Update imports and references in all affected files
- [x] Update configuration and environment variables

#### 2. Update Documentation
- [x] Update README.md to clarify the distinction between API and MCP
- [x] Add documentation about the API server's purpose and endpoints
- [x] Document the relationship between API and MCP servers

### Database Reset Script
- [x] Create `scripts/reset_databases.sh` to wipe all databases
- [x] Ensure script handles both PostgreSQL ('hades_test') and ArangoDB
- [x] Add safety checks to prevent accidental data loss
- [x] Test script functionality

### Phase 2: Implement MCP Server (Core)

#### 1. Basic MCP Server Setup
- [x] Create new MCP server implementation in `src/mcp/server.py`
- [x] Implement MCP protocol transport layer (WebSockets)
- [x] Implement basic message handling
- [x] Create configuration for MCP server

#### 2. First MCP Tool: Show All Databases
- [x] Implement tool registration mechanism
- [x] Create "show_databases" tool that lists all databases
- [x] Add authentication/authorization for MCP tools
- [x] Test the tool with an MCP client

## To Do Tasks

## Phase 3: Expand MCP Capabilities

### 1. Data Ingestion Tools
- [x] Implement "ingest_data" tool for adding data to knowledge graph
- [x] Add validation and error handling
- [x] Create scripts for batch ingestion of documentation
- [x] Ingest ArangoDB Python documentation into HADES
- [x] Add documentation for ingestion process (`docs/documentation_ingestion.md`)

### 2. Data Retrieval Tools
- [x] Implement "pathrag_retrieve" tool for retrieving data from knowledge graph
- [ ] Enhance PathRAG with context-aware retrieval
- [ ] Implement semantic search capabilities
- [ ] Create test cases for data ingestion
- [ ] Document the data format and requirements

### 3. Embedded Model Architecture Implementation
- [x] Create implementation plan document ([HADES_Embedded_Model_Implementation_Plan.md](HADES_Embedded_Model_Implementation_Plan.md))
- [ ] Implement model abstraction layer with LLMProcessor interface
- [ ] Create Ollama adapter implementing the LLMProcessor interface
- [ ] Develop ModelFactory for instantiating appropriate model adapters
- [ ] Integrate with document processing pipeline
- [ ] Enhance entity extraction capabilities using LLM
- [ ] Implement relationship mapping functionality
- [ ] Add model-powered context generation for queries
- [ ] Create configuration system for model selection and parameters
- [ ] Develop model caching mechanism for performance
- [ ] Write comprehensive tests for model swapping capabilities

### 4. ECL User Memory Implementation
- [x] Create user memory documentation ([docs/ECL_User_Memory_Implementation.md](docs/ECL_User_Memory_Implementation.md))
- [ ] Implement UserMemoryManager class
- [ ] Create directory structure for user memories
- [ ] Implement system monitoring components
- [ ] Add user memory MCP tools
- [ ] Integrate with PathRAG for memory retrieval
- [ ] Implement entity extraction from user observations
- [ ] Create relationship identification between memory entities
- [ ] Add user memory integration tests
- [ ] Develop memory access control mechanisms
- [ ] Implement memory consolidation and optimization

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
