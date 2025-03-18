#!/usr/bin/env python
"""
Sample Knowledge Ingestion Script

This script directly ingests knowledge about ArangoDB, MCP, and PathRAG
into the ArangoDB database without needing to scrape websites.
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import HADES modules
from src.db.arangodb_connection_fix_v2 import DirectArangoAPI
from src.utils.logger import get_logger

# Configure logging
logger = get_logger(__name__)

def create_sample_knowledge():
    """Create sample knowledge about ArangoDB, MCP, and PathRAG."""
    
    # Create entities for the main concepts
    entities = [
        # 1. ArangoDB
        {
            "id": "arangodb",
            "name": "ArangoDB",
            "type": "technology",
            "domain": "databases",
            "properties": {
                "description": "Multi-model NoSQL database with flexible data models for documents, graphs, and key-values.",
                "version": "3.11.5",
                "website": "https://www.arangodb.com/"
            },
            "relationships": [
                {"target": "multi_model_db", "type": "IS_A"},
                {"target": "graph_db", "type": "IS_A"},
                {"target": "nosql_db", "type": "IS_A"},
                {"target": "aql", "type": "HAS_COMPONENT"}
            ]
        },
        
        # 2. AQL (ArangoDB Query Language)
        {
            "id": "aql",
            "name": "AQL",
            "type": "technology",
            "domain": "databases",
            "properties": {
                "description": "ArangoDB Query Language, used to retrieve and modify data in ArangoDB.",
                "documentation": "https://www.arangodb.com/docs/stable/aql/"
            },
            "relationships": [
                {"target": "arangodb", "type": "PART_OF"}
            ]
        },
        
        # 3. Model Context Protocol (MCP)
        {
            "id": "mcp",
            "name": "Model Context Protocol",
            "type": "protocol",
            "domain": "ai",
            "properties": {
                "description": "Protocol for managing and accessing context in language models.",
                "paper": "https://arxiv.org/abs/2209.07663"
            },
            "relationships": [
                {"target": "hades", "type": "USED_BY"},
                {"target": "pathrag", "type": "USES"}
            ]
        },
        
        # 4. PathRAG
        {
            "id": "pathrag",
            "name": "PathRAG",
            "type": "technique",
            "domain": "ai",
            "properties": {
                "description": "Path-based Retrieval Augmented Generation, a technique for retrieving knowledge paths in a graph database for LLMs.",
                "paper": "https://arxiv.org/abs/2312.11702"
            },
            "relationships": [
                {"target": "rag", "type": "IS_A"},
                {"target": "knowledge_graphs", "type": "USES"},
                {"target": "arangodb", "type": "CAN_USE"}
            ]
        },
        
        # 5. HADES System
        {
            "id": "hades",
            "name": "HADES System",
            "type": "system",
            "domain": "ai",
            "properties": {
                "description": "Heuristic Adaptive Data Extrapolation System, an AI system for knowledge management and retrieval.",
                "repository": "https://github.com/r3d91ll/Heuristic-Adaptive-Data-Extrapolation-System-HADES"
            },
            "relationships": [
                {"target": "pathrag", "type": "INCORPORATES"},
                {"target": "mcp", "type": "IMPLEMENTS"},
                {"target": "arangodb", "type": "USES"}
            ]
        },
        
        # Supporting concepts
        {
            "id": "multi_model_db",
            "name": "Multi-model Database",
            "type": "concept",
            "domain": "databases",
            "properties": {
                "description": "Database system designed to support multiple data models against a single, integrated backend."
            },
            "relationships": []
        },
        {
            "id": "graph_db",
            "name": "Graph Database",
            "type": "concept",
            "domain": "databases",
            "properties": {
                "description": "Database designed to store data in a graph structure with nodes, edges, and properties."
            },
            "relationships": []
        },
        {
            "id": "nosql_db",
            "name": "NoSQL Database",
            "type": "concept",
            "domain": "databases",
            "properties": {
                "description": "Non-relational database that provides flexible schemas for storage and retrieval of data."
            },
            "relationships": []
        },
        {
            "id": "rag",
            "name": "Retrieval-Augmented Generation",
            "type": "technique",
            "domain": "ai",
            "properties": {
                "description": "Technique that combines information retrieval with text generation to enhance AI responses with external knowledge."
            },
            "relationships": []
        },
        {
            "id": "knowledge_graphs",
            "name": "Knowledge Graphs",
            "type": "concept",
            "domain": "ai",
            "properties": {
                "description": "Structure that integrates data by linking entities through semantic relationships."
            },
            "relationships": []
        }
    ]
    
    return {
        "entities": entities,
        "domain": "hades_knowledge"
    }

def ingest_knowledge():
    """Ingest sample knowledge into ArangoDB."""
    load_dotenv()
    
    # Initialize API connection
    api = DirectArangoAPI()
    
    # Ensure collections exist
    api.create_collection("entities")
    api.create_collection("edges", is_edge=True)
    
    # Get sample knowledge
    data = create_sample_knowledge()
    
    # Track created entities and relationships
    entities_created = 0
    relationships_created = 0
    
    # Process each entity
    for entity in data["entities"]:
        # Extract relationships before saving
        relationships = entity.pop("relationships", [])
        
        # Create entity
        entity_key = entity["id"]
        
        # Check if entity already exists
        existing_entity = api.execute_query(
            f"FOR e IN entities FILTER e._key == @key RETURN e",
            {"key": entity_key}
        )
        
        if existing_entity.get("result") and len(existing_entity["result"]) > 0:
            # Entity exists, update it
            api.execute_query(
                f"UPDATE @key WITH @entity IN entities",
                {"key": entity_key, "entity": entity}
            )
            print(f"Updated entity: {entity['name']}")
        else:
            # Create new entity
            api.execute_query(
                f"INSERT @entity INTO entities",
                {"entity": entity}
            )
            entities_created += 1
            print(f"Created entity: {entity['name']}")
        
        # Process relationships
        for rel in relationships:
            # Create edge
            from_id = f"entities/{entity_key}"
            to_id = f"entities/{rel['target']}"
            edge_data = {
                "_from": from_id,
                "_to": to_id,
                "type": rel["type"],
                "domain": data["domain"],
                "properties": rel.get("properties", {})
            }
            
            # Check if edge already exists
            existing_edge = api.execute_query(
                f"FOR e IN edges FILTER e._from == @from AND e._to == @to AND e.type == @type RETURN e",
                {"from": from_id, "to": to_id, "type": rel["type"]}
            )
            
            if existing_edge.get("result") and len(existing_edge["result"]) > 0:
                # Edge exists, update it
                edge_id = existing_edge["result"][0]["_key"]
                api.execute_query(
                    f"UPDATE @key WITH @edge IN edges",
                    {"key": edge_id, "edge": edge_data}
                )
                print(f"Updated relationship: {entity['name']} --[{rel['type']}]--> {rel['target']}")
            else:
                # Create new edge
                api.execute_query(
                    f"INSERT @edge INTO edges",
                    {"edge": edge_data}
                )
                relationships_created += 1
                print(f"Created relationship: {entity['name']} --[{rel['type']}]--> {rel['target']}")
    
    # Return results
    result = {
        "success": True,
        "ingested_count": {
            "entities": entities_created,
            "relationships": relationships_created
        },
        "domain": data["domain"],
        "timestamp": datetime.now().isoformat()
    }
    
    print("\nIngestion Results:")
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    ingest_knowledge()
