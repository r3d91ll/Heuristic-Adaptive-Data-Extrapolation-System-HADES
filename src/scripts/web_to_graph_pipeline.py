#!/usr/bin/env python
"""
Web to Knowledge Graph Pipeline

This script fetches content from websites, converts it to markdown,
extracts entities and relationships, and ingests them into the ArangoDB database.
"""

import os
import sys
import json
import logging
import requests
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import HADES modules
from src.db.arangodb_connection_fix_v2 import DirectArangoAPI
from src.utils.logger import get_logger

# Configure logging
logger = get_logger(__name__)

class WebToGraphPipeline:
    """Pipeline for converting web content to knowledge graph data."""
    
    def __init__(self):
        """Initialize the pipeline."""
        load_dotenv()
        
        # Initialize API connection
        self.api = DirectArangoAPI()
        
        # Ensure collections exist
        self.api.create_collection("entities")
        self.api.create_collection("edges", is_edge=True)
    
    def fetch_web_content(self, url):
        """
        Fetch content from a URL.
        
        Args:
            url: URL to fetch content from
            
        Returns:
            HTML content
        """
        logger.info(f"Fetching content from {url}")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def html_to_markdown(self, html_content):
        """
        Convert HTML to markdown.
        
        Args:
            html_content: HTML content to convert
            
        Returns:
            Markdown content
        """
        logger.info("Converting HTML to markdown")
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove scripts, styles, and navigation elements
        for element in soup(['script', 'style', 'nav', 'footer', 'aside']):
            element.decompose()
        
        # Convert to markdown
        markdown_content = md(str(soup))
        
        return markdown_content
    
    def extract_entities(self, markdown_content, domain, source_url):
        """
        Extract entities and relationships from markdown.
        This is a simplified version - in a real system, you might use NLP or
        other advanced techniques.
        
        Args:
            markdown_content: Markdown content to extract from
            domain: Domain for the entities
            source_url: Source URL for attribution
            
        Returns:
            Dictionary with entities and relationships
        """
        logger.info("Extracting entities and relationships")
        
        # Get the title from the first heading
        title_match = re.search(r'^# (.*?)$', markdown_content, re.MULTILINE)
        title = title_match.group(1) if title_match else "Untitled Document"
        
        # Create the main document entity
        document_id = f"doc_{urlparse(source_url).netloc.replace('.', '_')}"
        document_entity = {
            "id": document_id,
            "name": title,
            "type": "document",
            "domain": domain,
            "properties": {
                "source_url": source_url,
                "fetched_at": datetime.now().isoformat()
            },
            "relationships": []
        }
        
        # Extract section headings as concepts
        headings = re.findall(r'^## (.*?)$', markdown_content, re.MULTILINE)
        entities = [document_entity]
        
        for i, heading in enumerate(headings):
            concept_id = f"{document_id}_concept_{i}"
            
            # Create concept entity
            concept_entity = {
                "id": concept_id,
                "name": heading,
                "type": "concept",
                "domain": domain,
                "properties": {
                    "source_document": document_id
                },
                "relationships": []
            }
            
            # Add relationship from document to concept
            document_entity["relationships"].append({
                "target": concept_id,
                "type": "HAS_CONCEPT",
                "properties": {
                    "order": i
                }
            })
            
            entities.append(concept_entity)
        
        return {
            "entities": entities,
            "domain": domain
        }
    
    def ingest_data(self, data):
        """
        Ingest data into ArangoDB.
        
        Args:
            data: Dictionary with entities and relationships
            
        Returns:
            Ingestion result
        """
        logger.info(f"Ingesting {len(data['entities'])} entities")
        
        # Process each entity
        entities_created = 0
        relationships_created = 0
        
        for entity in data["entities"]:
            # Extract relationships before saving
            relationships = entity.pop("relationships", [])
            
            # Create entity
            entity_key = entity["id"]
            
            # Check if entity already exists
            existing_entity = self.api.execute_query(
                f"FOR e IN entities FILTER e._key == @key RETURN e",
                {"key": entity_key}
            )
            
            if existing_entity.get("result") and len(existing_entity["result"]) > 0:
                # Entity exists, update it
                self.api.execute_query(
                    f"UPDATE @key WITH @entity IN entities",
                    {"key": entity_key, "entity": entity}
                )
            else:
                # Create new entity
                self.api.execute_query(
                    f"INSERT @entity INTO entities",
                    {"entity": entity}
                )
                entities_created += 1
            
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
                existing_edge = self.api.execute_query(
                    f"FOR e IN edges FILTER e._from == @from AND e._to == @to AND e.type == @type RETURN e",
                    {"from": from_id, "to": to_id, "type": rel["type"]}
                )
                
                if existing_edge.get("result") and len(existing_edge["result"]) > 0:
                    # Edge exists, update it
                    edge_id = existing_edge["result"][0]["_key"]
                    self.api.execute_query(
                        f"UPDATE @key WITH @edge IN edges",
                        {"key": edge_id, "edge": edge_data}
                    )
                else:
                    # Create new edge
                    self.api.execute_query(
                        f"INSERT @edge INTO edges",
                        {"edge": edge_data}
                    )
                    relationships_created += 1
        
        return {
            "success": True,
            "ingested_count": {
                "entities": entities_created,
                "relationships": relationships_created
            },
            "domain": data["domain"],
            "timestamp": datetime.now().isoformat()
        }
    
    def process_url(self, url, domain="general"):
        """
        Process a URL through the entire pipeline.
        
        Args:
            url: URL to process
            domain: Domain for the entities
            
        Returns:
            Processing result
        """
        # Step 1: Fetch web content
        html_content = self.fetch_web_content(url)
        if not html_content:
            return {"success": False, "error": f"Failed to fetch content from {url}"}
        
        # Step 2: Convert to markdown
        markdown_content = self.html_to_markdown(html_content)
        
        # Step 3: Extract entities
        data = self.extract_entities(markdown_content, domain, url)
        
        # Step 4: Ingest data
        result = self.ingest_data(data)
        
        return result

def main():
    """Main entry point."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Web to Knowledge Graph Pipeline")
    parser.add_argument("urls", nargs="+", help="URLs to process")
    parser.add_argument("--domain", default="general", help="Domain for the entities")
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = WebToGraphPipeline()
    
    # Process each URL
    results = []
    for url in args.urls:
        result = pipeline.process_url(url, args.domain)
        results.append(result)
        
        print(f"Processed {url}:")
        print(json.dumps(result, indent=2))
    
    # Summary
    total_entities = sum(r.get("ingested_count", {}).get("entities", 0) for r in results if r.get("success", False))
    total_relationships = sum(r.get("ingested_count", {}).get("relationships", 0) for r in results if r.get("success", False))
    
    print(f"\nTotal ingested: {total_entities} entities, {total_relationships} relationships")

if __name__ == "__main__":
    main()
