#!/usr/bin/env python
"""
Populate the ArangoDB database with sample paths for testing - Version 2.

This script creates entities and edges in the ArangoDB database to test the PathRAG functionality.
It's designed to work with the existing collection structure in the database.
"""

import os
import sys
import json
import logging
import time
import uuid
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import HADES modules
from src.db.arangodb_connection_fix_v2 import DirectArangoAPI, get_client
from src.utils.logger import get_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

def query_collections(api):
    """
    Query the database to get a list of all collections.
    
    Args:
        api: DirectArangoAPI instance
        
    Returns:
        List of collection names
    """
    try:
        # Unfortunately we can't directly query _collections in ArangoDB using AQL
        # We need to use the REST API for this, but we'll work with what we know exists
        result = api.execute_query("RETURN COLLECTIONS()")
        
        if result.get("success", False):
            return result.get("result", [])
        else:
            logger.error(f"Failed to get collections: {result.get('error', 'Unknown error')}")
            # Return default set of collections we know should exist
            return ["entities", "edges", "facts", "relationships", "sources", "versions"]
    except Exception as e:
        logger.error(f"Error getting collections: {e}")
        return []

def create_entity(api, entity_key, name, domain="test_domain", description="", properties=None):
    """
    Create or update an entity in the ArangoDB database.
    
    Args:
        api: DirectArangoAPI instance
        entity_key: Key for the entity (used as _key in ArangoDB)
        name: Name of the entity
        domain: Domain the entity belongs to
        description: Description of the entity
        properties: Additional properties for the entity
        
    Returns:
        The entity ID or None if creation failed
    """
    if properties is None:
        properties = {}
        
    # Generate a unique entity_id if not provided
    entity_id = properties.get("entity_id", str(uuid.uuid4()))
    
    # Create entity document - structure matches what's in the database
    entity_doc = {
        "_key": entity_key,
        "name": name,
        "domain": domain,
        "description": description,
        "entity_id": entity_id,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
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
        "key": entity_key,
        "doc": entity_doc
    }
    
    result = api.execute_query(query, bind_vars=bind_vars)
    
    if result.get("success", False):
        logger.info(f"Created/updated entity: {name} (Key: {entity_key})")
        return entity_key
    else:
        logger.error(f"Failed to create entity {name}: {result.get('error', 'Unknown error')}")
        return None

def create_relationship(api, from_key, to_key, rel_type, properties=None):
    """
    Create a relationship between two entities in the ArangoDB database.
    
    Args:
        api: DirectArangoAPI instance
        from_key: Key of the source entity
        to_key: Key of the target entity
        rel_type: Type of relationship
        properties: Additional properties for the relationship
        
    Returns:
        True if the relationship was created successfully, False otherwise
    """
    if properties is None:
        properties = {}
        
    # Generate a unique ID for the relationship
    rel_id = str(uuid.uuid4())
    
    # Create relationship document
    rel_doc = {
        "_key": rel_id,
        "from_entity": from_key,
        "to_entity": to_key,
        "type": rel_type,
        "domain": "test_domain",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        **properties
    }
    
    # Execute query to create relationship
    query = """
    INSERT @doc INTO relationships
    RETURN NEW
    """
    
    bind_vars = {
        "doc": rel_doc
    }
    
    rel_result = api.execute_query(query, bind_vars=bind_vars)
    
    if not rel_result.get("success", False):
        logger.error(f"Failed to create relationship: {rel_result.get('error', 'Unknown error')}")
        return False
        
    # Create the edge in the edges collection
    edge_doc = {
        "_from": f"entities/{from_key}",
        "_to": f"entities/{to_key}",
        "relationship_id": rel_id,
        "type": rel_type,
        "domain": "test_domain",
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }
    
    # Execute query to create edge
    query = """
    INSERT @doc INTO edges
    RETURN NEW
    """
    
    bind_vars = {
        "doc": edge_doc
    }
    
    edge_result = api.execute_query(query, bind_vars=bind_vars)
    
    if edge_result.get("success", False):
        logger.info(f"Created edge: {from_key} -> {to_key} ({rel_type})")
        return True
    else:
        logger.error(f"Failed to create edge: {edge_result.get('error', 'Unknown error')}")
        return False

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
        
        # Check what collections exist
        collections = query_collections(api)
        logger.info(f"Collections: {collections}")
        
        # Define sample entities
        entities = [
            {"key": "arangodb", "name": "ArangoDB", "description": "A multi-model database system.", "properties": {"type": "database"}},
            {"key": "nosql", "name": "NoSQL", "description": "A type of database that doesn't use SQL.", "properties": {"type": "concept"}},
            {"key": "database", "name": "Database", "description": "A system for storing and retrieving data.", "properties": {"type": "concept"}},
            {"key": "graph_database", "name": "Graph Database", "description": "A database that uses graph structures.", "properties": {"type": "concept"}},
            {"key": "key_value_store", "name": "Key-Value Store", "description": "A simple database that stores key-value pairs.", "properties": {"type": "concept"}},
            {"key": "document_store", "name": "Document Store", "description": "A database that stores documents.", "properties": {"type": "concept"}},
            {"key": "multi_model_database", "name": "Multi-model Database", "description": "A database that supports multiple data models.", "properties": {"type": "concept"}},
            {"key": "aql", "name": "AQL", "description": "ArangoDB Query Language", "properties": {"type": "concept"}},
            {"key": "graphql", "name": "GraphQL", "description": "A query language for APIs.", "properties": {"type": "concept"}},
            {"key": "sql", "name": "SQL", "description": "Structured Query Language", "properties": {"type": "concept"}},
            {"key": "json", "name": "JSON", "description": "JavaScript Object Notation", "properties": {"type": "concept"}},
            {"key": "pathrag", "name": "PathRAG", "description": "Path-based Retrieval Augmented Generation", "properties": {"type": "concept"}},
            {"key": "hades", "name": "HADES", "description": "Heuristic Adaptive Data Extrapolation System", "properties": {"type": "system"}}
        ]
        
        # Create entities
        entity_keys = {}
        for entity in entities:
            key = create_entity(api, entity["key"], entity["name"], "test_domain", entity["description"], entity["properties"])
            if key:
                entity_keys[entity["name"]] = key
        
        # Check if entities were created
        result = api.execute_query("FOR e IN entities FILTER e.domain == 'test_domain' RETURN e.name")
        if result.get("success", False):
            created_entities = result.get("result", [])
            logger.info(f"Created entities: {created_entities}")
        
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
            {"from": "PathRAG", "to": "Graph Database", "type": "uses"}
        ]
        
        # Create relationships
        for rel in relationships:
            if rel["from"] in entity_keys and rel["to"] in entity_keys:
                from_key = entity_keys[rel["from"]]
                to_key = entity_keys[rel["to"]]
                create_relationship(api, from_key, to_key, rel["type"])
        
        # Test a query to get paths
        logger.info("Testing path query...")
        query = """
        FOR v, e, p IN 1..3 OUTBOUND 'entities/arangodb' edges
            RETURN {
                "path": CONCAT_SEPARATOR(' -> ', p.vertices[*].name),
                "vertices": p.vertices[*].name
            }
        """
        
        result = api.execute_query(query)
        
        if result.get("success", False):
            paths = result.get("result", [])
            if paths:
                logger.info(f"Found {len(paths)} paths from ArangoDB:")
                for i, path in enumerate(paths):
                    logger.info(f"  Path {i+1}: {path.get('path', '')}")
            else:
                logger.info("No paths found.")
        else:
            logger.error(f"Path query failed: {result.get('error', 'Unknown error')}")
        
        logger.info("Sample data population complete!")
        return True
    except Exception as e:
        logger.error(f"Error populating sample data: {e}")
        return False

if __name__ == "__main__":
    print("=== Populating ArangoDB with sample data (v2) ===")
    success = populate_sample_data()
    if success:
        print("Sample data population successful!")
    else:
        print("Sample data population failed!")
