"""
Tests for the DBConnection module using real ArangoDB connections.
"""
import pytest
import uuid
from datetime import datetime

# Import the DBConnection class
from src.db.connection import DBConnection, get_db_connection

# Skip these tests if arango is not installed
pytest.importorskip("arango")

class TestRealDBConnection:
    """Test the DBConnection class with real ArangoDB connections."""

    def test_connect(self, arango_connection_params):
        """Test connecting to ArangoDB."""
        db_conn = DBConnection(db_name=arango_connection_params["database"])
        
        # Connect to the database
        connected = db_conn.connect(
            host=arango_connection_params["host"],
            username=arango_connection_params["username"],
            password=arango_connection_params["password"]
        )
        
        assert connected is True
        assert db_conn.db is not None

    def test_execute_query(self, real_db_connection, clean_test_collections, arango_db):
        """Test executing a query on ArangoDB."""
        # Insert a test document
        test_id = f"test_{uuid.uuid4()}"
        test_doc = {
            "_key": test_id,
            "name": "Test Entity",
            "description": "Test entity for query execution",
            "created_at": datetime.now().isoformat()
        }
        
        collection = arango_db.collection("test_entities")
        collection.insert(test_doc)
        
        # Execute a query to retrieve the document
        query = "FOR doc IN test_entities FILTER doc._key == @key RETURN doc"
        bind_vars = {"key": test_id}
        
        result = real_db_connection.execute_query(query, bind_vars)
        
        # Verify the query was successful
        assert result["success"] is True
        assert len(result["result"]) == 1
        assert result["result"][0]["name"] == "Test Entity"

    def test_get_db_connection(self, arango_connection_params):
        """Test the get_db_connection function."""
        # Get a database connection
        db_conn = get_db_connection(
            db_name=arango_connection_params["database"],
            host=arango_connection_params["host"],
            username=arango_connection_params["username"],
            password=arango_connection_params["password"]
        )
        
        # Verify the connection was successful
        assert db_conn is not None
        assert isinstance(db_conn, DBConnection)
        assert db_conn.db is not None

    def test_version_aware_query(self, real_db_connection, clean_test_collections, arango_db):
        """Test executing a version-aware query on ArangoDB."""
        # Insert test documents with different versions
        collection = arango_db.collection("test_entities")
        
        # Document with version 1
        doc1 = {
            "_key": f"test_v1_{uuid.uuid4()}",
            "name": "Entity v1",
            "version": "1.0.0",
            "created_at": "2025-01-01T00:00:00"
        }
        
        # Document with version 2
        doc2 = {
            "_key": f"test_v2_{uuid.uuid4()}",
            "name": "Entity v2",
            "version": "2.0.0",
            "created_at": "2025-02-01T00:00:00"
        }
        
        # Insert documents
        collection.insert(doc1)
        collection.insert(doc2)
        
        # Execute a version-aware query
        query = "FOR doc IN test_entities RETURN doc"
        
        # Query as of version 1.0.0
        result1 = real_db_connection.execute_query(
            query,
            bind_vars={},
            as_of_version="1.0.0"
        )
        
        # Query as of version 2.0.0
        result2 = real_db_connection.execute_query(
            query,
            bind_vars={},
            as_of_version="2.0.0"
        )
        
        # Verify the queries were successful
        assert result1["success"] is True
        assert result2["success"] is True
        
        # Version 1.0.0 should only return the first document
        v1_docs = [doc for doc in result1["result"] if doc.get("version") in ["1.0.0"]]
        assert len(v1_docs) == 1
        
        # Version 2.0.0 should return both documents
        v2_docs = [doc for doc in result2["result"] if doc.get("version") in ["1.0.0", "2.0.0"]]
        assert len(v2_docs) == 2

    def test_error_handling(self, real_db_connection):
        """Test error handling in execute_query."""
        # Execute an invalid query
        query = "FOR doc IN non_existent_collection RETURN doc"
        
        result = real_db_connection.execute_query(query)
        
        # Verify the query failed
        assert result["success"] is False
        assert "error" in result
