#!/usr/bin/env python
"""
Populate the ArangoDB database with sample paths for testing.

This script creates entities and edges in the ArangoDB database to test the PathRAG functionality.
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import HADES modules
from src.db.arangodb_connection_fix_v2 import DirectArangoAPI, get_client
from src.utils.logger import get_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

def create_entity(api, name, properties=None):
    """
    Create an entity in the ArangoDB database.
    
    Args:
        api: DirectArangoAPI instance
        name: Name of the entity
        properties: Additional properties for the entity
        
    Returns:
        The created entity document or None if creation failed
    """
    if properties is None:
        properties = {}
        
    # Create entity document
    entity_doc = {
        "_key": name,
        "name": name,
        "domain": "test_domain",
        **properties
    }
    
    # Execute query to create entity
    query = """
    UPSERT { _key: @key }
    INSERT @doc
    UPDATE @doc
    IN entities
    RETURN NEW
    """
    
    bind_vars = {
        "key": name,
        "doc": entity_doc
    }
    
    result = api.execute_query(query, bind_vars=bind_vars)
    
    if result.get("success", False):
        logger.info(f"Created/updated entity: {name}")
        return result["result"][0]
    else:
        logger.error(f"Failed to create entity {name}: {result.get('error', 'Unknown error')}")
        return None
        
def create_edge(api, from_entity, to_entity, relationship_type="related_to", properties=None):
    """
    Create an edge between two entities in the ArangoDB database.
    
    Args:
        api: DirectArangoAPI instance
        from_entity: Name of the source entity
        to_entity: Name of the target entity
        relationship_type: Type of relationship
        properties: Additional properties for the edge
        
    Returns:
        The created edge document or None if creation failed
    """
    if properties is None:
        properties = {}
        
    # Create edge document
    edge_doc = {
        "_from": f"entities/{from_entity}",
        "_to": f"entities/{to_entity}",
        "type": relationship_type,
        "domain": "test_domain",
        **properties
    }
    
    # Execute query to create edge
    query = """
    UPSERT { _from: @from, _to: @to, type: @type }
    INSERT @doc
    UPDATE @doc
    IN edges
    RETURN NEW
    """
    
    bind_vars = {
        "from": f"entities/{from_entity}",
        "to": f"entities/{to_entity}",
        "type": relationship_type,
        "doc": edge_doc
    }
    
    result = api.execute_query(query, bind_vars=bind_vars)
    
    if result.get("success", False):
        logger.info(f"Created/updated edge: {from_entity} -> {to_entity} ({relationship_type})")
        return result["result"][0]
    else:
        logger.error(f"Failed to create edge {from_entity} -> {to_entity}: {result.get('error', 'Unknown error')}")
        return None

def ensure_collections_exist(api):
    """
    Ensure the required collections exist in the database.
    
    Args:
        api: DirectArangoAPI instance
    """
    # Create entities collection if it doesn't exist
    query = """
    FOR c IN _collections
        FILTER c.name == "entities"
        RETURN c
    """
    
    result = api.execute_query(query)
    
    if result.get("success", False) and not result.get("result", []):
        create_collection_query = """
        CREATE COLLECTION entities
        """
        api.execute_query(create_collection_query)
        logger.info("Created entities collection")
    
    # Create edges collection if it doesn't exist
    query = """
    FOR c IN _collections
        FILTER c.name == "edges"
        RETURN c
    """
    
    result = api.execute_query(query)
    
    if result.get("success", False) and not result.get("result", []):
        create_collection_query = """
        CREATE EDGE COLLECTION edges
        """
        api.execute_query(create_collection_query)
        logger.info("Created edges collection")

def populate_sample_data():
    """
    Populate the ArangoDB database with sample data for testing.
    """
    # Load environment variables
    load_dotenv()
    
    # Get ArangoDB credentials from environment
    arango_host = os.environ.get("HADES_ARANGO_HOST", "localhost")
    arango_port = os.environ.get("HADES_ARANGO_PORT", "8529")
    arango_user = os.environ.get("HADES_ARANGO_USER", "hades")
    arango_password = os.environ.get("HADES_ARANGO_PASSWORD", "LVlX5fshvf0H24cWQNHjm41S")
    arango_db_name = os.environ.get("HADES_ARANGO_DATABASE", "hades_graph")
    
    # Log loaded environment variables
    logger.info(f"ArangoDB Host: {arango_host}")
    logger.info(f"ArangoDB Port: {arango_port}")
    logger.info(f"ArangoDB User: {arango_user}")
    logger.info(f"ArangoDB Password: {'*' * len(arango_password) if arango_password else 'Not Set'}")
    logger.info(f"ArangoDB Database: {arango_db_name}")
    
    # Create DirectArangoAPI instance
    try:
        logger.info("Creating DirectArangoAPI instance...")
        api = DirectArangoAPI(
            host=arango_host,
            port=arango_port,
            username=arango_user,
            password=arango_password,
            database=arango_db_name
        )
        
        logger.info(f"DirectArangoAPI initialized with base URL: {api.base_url}")
        
        # Ensure collections exist
        ensure_collections_exist(api)
        
        # Define sample entities and relationships
        entities = [
            {"name": "ArangoDB", "properties": {"description": "A multi-model database system.", "type": "database"}},
            {"name": "NoSQL", "properties": {"description": "A type of database that doesn't use SQL.", "type": "concept"}},
            {"name": "Database", "properties": {"description": "A system for storing and retrieving data.", "type": "concept"}},
            {"name": "Graph Database", "properties": {"description": "A database that uses graph structures.", "type": "concept"}},
            {"name": "Key-Value Store", "properties": {"description": "A simple database that stores key-value pairs.", "type": "concept"}},
            {"name": "Document Store", "properties": {"description": "A database that stores documents.", "type": "concept"}},
            {"name": "Multi-model Database", "properties": {"description": "A database that supports multiple data models.", "type": "concept"}},
            {"name": "AQL", "properties": {"description": "ArangoDB Query Language", "type": "concept"}},
            {"name": "GraphQL", "properties": {"description": "A query language for APIs.", "type": "concept"}},
            {"name": "SQL", "properties": {"description": "Structured Query Language", "type": "concept"}},
            {"name": "JSON", "properties": {"description": "JavaScript Object Notation", "type": "concept"}},
            {"name": "PathRAG", "properties": {"description": "Path-based Retrieval Augmented Generation", "type": "concept"}},
            {"name": "HADES", "properties": {"description": "Heuristic Adaptive Data Extrapolation System", "type": "system"}},
        ]
        
        # Create entities
        created_entities = {}
        for entity_info in entities:
            entity = create_entity(api, entity_info["name"], entity_info.get("properties", {}))
            if entity:
                created_entities[entity_info["name"]] = entity
        
        # Define relationships
        relationships = [
            {"from": "ArangoDB", "to": "NoSQL", "type": "is_a"},
            {"from": "ArangoDB", "to": "Database", "type": "is_a"},
            {"from": "ArangoDB", "to": "Graph Database", "type": "implements"},
            {"from": "ArangoDB", "to": "Key-Value Store", "type": "implements"},
            {"from": "ArangoDB", "to": "Document Store", "type": "implements"},
            {"from": "ArangoDB", "to": "Multi-model Database", "type": "is_a"},
            {"from": "ArangoDB", "to": "AQL", "type": "uses"},
            {"from": "AQL", "to": "SQL", "type": "similar_to"},
            {"from": "AQL", "to": "GraphQL", "type": "different_from"},
            {"from": "Document Store", "to": "JSON", "type": "uses"},
            {"from": "PathRAG", "to": "ArangoDB", "type": "uses"},
            {"from": "HADES", "to": "PathRAG", "type": "uses"},
            {"from": "HADES", "to": "ArangoDB", "type": "uses"},
            {"from": "PathRAG", "to": "Graph Database", "type": "uses"},
        ]
        
        # Create relationships
        for rel in relationships:
            create_edge(api, rel["from"], rel["to"], rel["type"])
            
        # Create bi-directional relationships for better traversal
        for rel in relationships:
            reverse_type = f"reverse_{rel['type']}"
            create_edge(api, rel["to"], rel["from"], reverse_type)
        
        logger.info("Sample data population complete!")
        
        # Test a simple path query
        logger.info("Testing path query...")
        query = """
        FOR v, e, p IN 1..3 OUTBOUND 'entities/ArangoDB' edges
            RETURN {
                "path": CONCAT_SEPARATOR(' -> ', p.vertices[*].name),
                "vertices": p.vertices[*].name,
                "score": LENGTH(p.vertices)
            }
        """
        
        result = api.execute_query(query)
        
        if result.get("success", False):
            paths = result.get("result", [])
            if paths:
                logger.info(f"Found {len(paths)} paths from ArangoDB:")
                for i, path in enumerate(paths):
                    logger.info(f"  Path {i+1}: {path.get('path', 'Unknown path')}")
            else:
                logger.info("No paths found.")
        else:
            logger.error(f"Path query failed: {result.get('error', 'Unknown error')}")
        
        return True
    except Exception as e:
        logger.error(f"Error populating sample data: {e}")
        return False

if __name__ == "__main__":
    print("=== Populating ArangoDB with sample data ===")
    success = populate_sample_data()
    if success:
        print("Sample data population successful!")
    else:
        print("Sample data population failed!")
