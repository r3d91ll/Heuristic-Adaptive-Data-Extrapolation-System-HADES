import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pydantic import ValidationError
from HADES_MCP_Server import (
    DatabaseConfig,
    MilvusConfig,
    ServerConfig,
    QueryArgs,
    VectorSearchArgs,
    HybridSearchArgs,
    MCPError,
    ConnectionManager,
    VectorDBMCPServer,
    CallToolRequest,
    ListToolsRequest
)
import time

# Test DatabaseConfig
def test_database_config_defaults():
    config = DatabaseConfig()
    assert config.url == "http://localhost:8529"
    assert config.database == "_system"
    assert config.username == "root"
    assert config.password == ""
    assert config.container_name == "hades_arangodb"
    assert config.port == 8529
    assert config.root_password == "your_secure_password"
    assert config.data_volume == "hades_arango_data"
    assert config.apps_volume == "hades_arango_apps"

def test_database_config_validation():
    with pytest.raises(ValidationError):
        DatabaseConfig(url="invalid_url")  # Invalid URL to trigger validation error

# Test MilvusConfig
def test_milvus_config_defaults():
    config = MilvusConfig()
    assert config.host == "localhost"
    assert config.port == 19530
    assert config.username == "root"
    assert config.password == "your_secure_password"
    assert config.container_name == "hades_milvus"
    assert config.data_volume == "hades_milvus_data"

def test_milvus_config_port_validation():
    with pytest.raises(ValidationError):
        MilvusConfig(port=65536)

# Test ServerConfig
def test_server_config_defaults():
    config = ServerConfig()
    assert config.thread_pool_size == 5
    assert config.max_concurrent_requests == 100
    assert config.request_timeout == 30.0
    assert config.etcd_container_name == "hades_etcd"
    assert config.minio_container_name == "hades_minio"
    assert config.etcd_data_volume == "hades_etcd_data"
    assert config.minio_data_volume == "hades_minio_data"
    assert config.docker_network_name == "hades_network"

def test_server_config_validation():
    with pytest.raises(ValidationError):
        ServerConfig(thread_pool_size=-1)  # Invalid thread pool size

# Test QueryArgs
def test_query_args_valid():
    args = QueryArgs(query="FOR doc IN collection RETURN doc")
    assert args.query == "FOR doc IN collection RETURN doc"
    assert args.bind_vars is None

def test_query_args_invalid_empty():
    with pytest.raises(ValidationError):
        QueryArgs(query="")

def test_query_args_invalid_whitespace():
    with pytest.raises(ValidationError):
        QueryArgs(query="   ")

# Test VectorSearchArgs
def test_vector_search_args_valid():
    args = VectorSearchArgs(collection="test_collection", vector=[0.1, 0.2, 0.3])
    assert args.collection == "test_collection"
    assert args.vector == [0.1, 0.2, 0.3]
    assert args.limit == 5
    assert args.filters is None

def test_vector_search_args_invalid_empty_vector():
    with pytest.raises(ValidationError):
        VectorSearchArgs(collection="test_collection", vector=[])

# Test HybridSearchArgs
def test_hybrid_search_args_valid():
    args = HybridSearchArgs(
        milvus_collection="test_milvus",
        arango_collection="test_arango",
        query_text="search text",
        vector=[0.1, 0.2, 0.3]
    )
    assert args.milvus_collection == "test_milvus"
    assert args.arango_collection == "test_arango"
    assert args.query_text == "search text"
    assert args.vector == [0.1, 0.2, 0.3]
    assert args.limit == 5
    assert args.filters is None

def test_hybrid_search_args_invalid_empty_vector():
    with pytest.raises(ValidationError):
        HybridSearchArgs(
            milvus_collection="test_milvus",
            arango_collection="test_arango",
            query_text="search text",
            vector=[],  # Invalid empty vector to trigger validation error
            limit=5
        )

# Test ConnectionManager
@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections.connect', new_callable=AsyncMock)
async def test_connection_manager_get_db(mock_connect, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)
    
    # Mock ArangoDB client and database
    mock_arango_client_instance = MagicMock()
    mock_database = MagicMock()
    mock_connect.return_value = mock_arango_client_instance
    mock_arango_client_instance.db.return_value = mock_database
    
    db = await conn_manager.get_db()
    assert db == mock_database

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections.connect', new_callable=AsyncMock)
async def test_connection_manager_get_db_retry(mock_connect, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)
    
    # Mock ArangoDB client and database with retry logic
    mock_arango_client_instance = MagicMock()
    mock_database = MagicMock()
    mock_connect.side_effect = [Exception("Connection failed"), mock_arango_client_instance]
    mock_arango_client_instance.db.return_value = mock_database
    
    db = await conn_manager.get_db()
    assert db == mock_database

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections.connect', new_callable=AsyncMock)
async def test_connection_manager_get_db_failure(mock_connect, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)
    
    # Mock ArangoDB client and database with failure
    mock_arango_client_instance = MagicMock()
    mock_database = MagicMock()
    mock_connect.side_effect = Exception("Connection failed")
    
    with pytest.raises(MCPError):
        await conn_manager.get_db()

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections.connect', new_callable=AsyncMock)
async def test_connection_manager_ensure_milvus(mock_connect, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)
    
    # Mock Milvus connection
    await conn_manager.ensure_milvus()
    assert conn_manager._milvus_connected is True

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections.connect', new_callable=AsyncMock)
async def test_connection_manager_ensure_milvus_retry(mock_connect, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)
    
    # Mock Milvus connection with retry logic
    mock_client.side_effect = [Exception("Connection failed"), None]
    await conn_manager.ensure_milvus()
    assert conn_manager._milvus_connected is True

@patch('HADES_MCP_Server.ArangoClient')
@patch('HADES_MCP_Server.connections.connect', new_callable=AsyncMock)
async def test_connection_manager_ensure_milvus_retry_failure(mock_connect, mock_client):
    db_config = DatabaseConfig()
    milvus_config = MilvusConfig()
    conn_manager = ConnectionManager(db_config, milvus_config)
    
    # Mock Milvus connection with retry logic
    mock_client.side_effect = Exception("Connection failed")
    await conn_manager.ensure_milvus()
    assert not conn_manager._milvus_connected

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
def test_vector_db_mcp_server_init(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    assert server.name == "vector-db-mcp-server"
    assert isinstance(server.server_config, ServerConfig)
    assert isinstance(server.db_config, DatabaseConfig)
    assert isinstance(server.milvus_config, MilvusConfig)
    assert isinstance(server.conn_manager, ConnectionManager)
    assert isinstance(server._executor, ThreadPoolExecutor)
    assert server.tools == {}
    assert server._tool_schemas_cache == {}

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
def test_vector_db_mcp_server_register_tools(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    server._register_tools()
    assert len(server.tools) > 0
    for tool_name, info in server.tools.items():
        assert "description" in info
        assert "handler" in info
        assert "schema" in info

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
def test_vector_db_mcp_server_register_handler(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    handler_mock = MagicMock()
    request_mock = ListToolsRequest(method="tools/list")
    server.register_handler(request_mock, handler_mock)
    assert server._handlers[request_mock] == handler_mock

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_handle_request(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    request_mock = MagicMock(method="GET")
    handler_mock = AsyncMock(return_value="response")
    server.register_handler(type(request_mock), handler_mock)
    
    response = await server.handle_request(request_mock)
    assert response == "response"
    handler_mock.assert_called_once_with(request_mock)

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_handle_request_no_handler(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    request_mock = MagicMock(method="tools/call", params=CallToolRequest(name="invalid_tool", arguments={}))
    
    with pytest.raises(MCPError) as excinfo:
        await server.handle_request(request_mock)
    assert "REQUEST_TYPE_NOT_FOUND" in str(excinfo.value)

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_execute_query(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    query_args = QueryArgs(query="FOR doc IN collection RETURN doc")
    
    # Mock connection manager and database
    mock_db = MagicMock()
    mock_conn_manager.get_db.return_value = mock_db
    
    # Mock aql execute
    mock_aql_execute = MagicMock(return_value=[{"key": "value"}])
    server._executor.submit.return_value.result.return_value = mock_aql_execute
    
    result = await server.execute_query(query_args.query, query_args.bind_vars)
    assert result == [{"key": "value"}]
    mock_db.aql.execute.assert_called_once_with(query_args.query, bind_vars=query_args.bind_vars or {})

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_execute_query_error(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    query_args = QueryArgs(query="FOR doc IN collection RETURN doc")
    
    # Mock connection manager and database
    mock_db = MagicMock()
    mock_conn_manager.get_db.return_value = mock_db
    
    # Mock aql execute with error
    mock_aql_execute = MagicMock(side_effect=Exception("Query failed"))
    server._executor.submit.return_value.result.return_value = mock_aql_execute
    
    with pytest.raises(MCPError) as excinfo:
        await server.execute_query(query_args.query, query_args.bind_vars)
    assert "QUERY_ERROR" in str(excinfo.value)

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_hybrid_search(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    search_args = HybridSearchArgs(
        milvus_collection="test_milvus",
        arango_collection="test_arango",
        query_text="search text",
        vector=[0.1, 0.2, 0.3]
    )
    
    # Mock connection manager and database
    mock_db = MagicMock()
    mock_conn_manager.get_db.return_value = mock_db
    
    # Mock Milvus collection search
    mock_collection = MagicMock()
    mock_search_result = MagicMock()
    mock_search_result[0] = [MagicMock(id=1)]
    mock_collection.search.return_value = mock_search_result
    server.conn_manager.ensure_milvus = AsyncMock()
    
    result = await server.hybrid_search(search_args)
    assert result == [{"key": "value"}]
    mock_collection.search.assert_called_once()
    mock_db.aql.execute.assert_called_once()

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_hybrid_search_error(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    search_args = HybridSearchArgs(
        milvus_collection="test_milvus",
        arango_collection="test_arango",
        query_text="search text",
        vector=[0.1, 0.2, 0.3]
    )
    
    # Mock connection manager and database
    mock_db = MagicMock()
    mock_conn_manager.get_db.return_value = mock_db
    
    # Mock Milvus collection search with error
    server.conn_manager.ensure_milvus = AsyncMock(side_effect=Exception("Milvus failed"))
    
    with pytest.raises(MCPError) as excinfo:
        await server.hybrid_search(search_args)
    assert "HYBRID_SEARCH_ERROR" in str(excinfo.value)

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_handle_list_tools(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    request_mock = ListToolsRequest(method="tools/list")
    
    response = await server.handle_list_tools(request_mock)
    assert "tools" in response
    for tool_info in response["tools"]:
        assert "name" in tool_info
        assert "description" in tool_info
        assert "inputSchema" in tool_info

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_handle_call_tool(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    request_mock = CallToolRequest(method="tools/call", params={"name": "execute_query", "arguments": {"query": "FOR doc IN collection RETURN doc"}})
    
    response = await server.handle_call_tool(request_mock)
    assert response["success"] is True

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_handle_call_tool_invalid_tool(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    request_mock = CallToolRequest(method="tools/call", params={"name": "invalid_tool", "arguments": {}})
    
    with pytest.raises(MCPError) as excinfo:
        await server.handle_call_tool(request_mock)
    assert "TOOL_NOT_FOUND" in str(excinfo.value)

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_handle_call_tool_validation_error(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    request_mock = CallToolRequest(method="tools/call", params={"name": "execute_query", "arguments": {"query": ""}})
    
    response = await server.handle_call_tool(request_mock)
    assert response["success"] is False
    assert "VALIDATION_ERROR" in response["error"]["code"]

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_handle_call_tool_timeout(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    request_mock = CallToolRequest(method="tools/call", params={"name": "execute_query", "arguments": {"query": "FOR doc IN collection RETURN doc"}})
    
    # Mock tool handler with timeout
    server.tools["execute_query"]["handler"] = AsyncMock(side_effect=asyncio.TimeoutError)
    
    response = await server.handle_call_tool(request_mock)
    assert response["success"] is False
    assert "TIMEOUT_ERROR" in response["error"]["code"]

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_health_check(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    server.start_time = time.time()  # Initialize start_time
    
    # Mock connection manager and database
    mock_db = MagicMock()
    mock_conn_manager.get_db.return_value = mock_db
    
    # Mock Milvus connection
    server.conn_manager.ensure_milvus = AsyncMock()
    
    status = await server.health_check()
    assert status["status"] == "ok"
    assert "uptime" in status
    assert status["connections"]["arango"] is True
    assert status["connections"]["milvus"] is True

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_health_check_arango_failure(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    server.start_time = time.time()  # Initialize start_time
    
    # Mock connection manager and database with failure
    mock_conn_manager.get_db.side_effect = Exception("Arango failed")
    
    status = await server.health_check()
    assert status["status"] == "degraded"
    assert "errors" in status
    assert "arango" in status["errors"]

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
async def test_vector_db_mcp_server_health_check_milvus_failure(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    server.start_time = time.time()  # Initialize start_time
    
    # Mock connection manager and database
    mock_db = MagicMock()
    mock_conn_manager.get_db.return_value = mock_db
    
    # Mock Milvus connection with failure
    server.conn_manager.ensure_milvus = AsyncMock(side_effect=Exception("Milvus failed"))
    
    status = await server.health_check()
    assert status["status"] == "degraded"
    assert "errors" in status
    assert "milvus" in status["errors"]

@patch('HADES_MCP_Server.ConnectionManager')
@patch('HADES_MCP_Server.ThreadPoolExecutor')
def test_vector_db_mcp_server_close(mock_executor, mock_conn_manager):
    server = VectorDBMCPServer()
    
    # Mock connection manager and database
    mock_arango_client_instance = MagicMock()
    mock_database = MagicMock()
    mock_conn_manager.return_value._client = mock_arango_client_instance
    mock_conn_manager.return_value._db = mock_database
    
    server.close()
    assert mock_arango_client_instance.close.assert_called_once_with()
    assert mock_conn_manager.return_value._executor.shutdown.assert_called_once_with(wait=True)
