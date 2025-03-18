#!/usr/bin/env python3
"""
Demo script for using the HADES MCP tools for ArangoDB documentation
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import argparse

# Add the parent directory to the path to import HADES modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, project_root)

# Define demo queries
DEMO_QUERIES = [
    "How to create a collection in ArangoDB using Python?",
    "How to execute an AQL query in Python?",
    "What is a graph in ArangoDB?",
    "How to create indexes in ArangoDB using Python?",
    "How to perform transactions in ArangoDB?"
]

def demo_direct_api():
    """
    Attempt to demonstrate retrieval using direct API access
    """
    try:
        # Try to import the PathRAG client
        from src.mcp.clients.pathrag import PathRAGClient
        
        print("Successfully imported PathRAG client. Running queries...")
        
        client = PathRAGClient()
        
        for query in DEMO_QUERIES:
            print(f"\n{'=' * 80}")
            print(f"Query: {query}")
            try:
                result = client.retrieve_paths(query, domain_filter="python-arango-docs", max_paths=3)
                print(f"Result: {json.dumps(result, indent=2)}")
            except Exception as e:
                print(f"Error: {e}")
            print(f"{'=' * 80}")
            
        return True
        
    except ImportError as e:
        print(f"Could not import PathRAG client: {e}")
        return False

def demo_windsurf_commands():
    """
    Demonstrate retrieval using Windsurf commands
    """
    print("\nTo retrieve information from HADES via Windsurf, you can use the following commands:")
    
    for i, query in enumerate(DEMO_QUERIES, 1):
        print(f"\n{i}. Query: '{query}'")
        print("   Windsurf command:")
        print("   ```")
        print("   mcp0_pathrag_retrieve:")
        print(f"     query: {query}")
        print("     domain_filter: python-arango-docs")
        print("     max_paths: 3")
        print("   ```")
    
def demo_command_line():
    """
    Demonstrate retrieval using command line
    """
    print("\nTo retrieve information from HADES via command line, run:")
    
    for i, query in enumerate(DEMO_QUERIES, 1):
        print(f"\n{i}. Query: '{query}'")
        print("   Command:")
        print(f"   python src/test_arango_docs.py retrieve --query \"{query}\" --domain python-arango-docs")

def demo_staging_directory():
    """
    Demonstrate how to inspect the staging directory
    """
    print("\nTo inspect the staging directory and check batch files:")
    print("\n1. Command:")
    print("   python src/test_arango_docs.py inspect --domain python-arango-docs")
    
    print("\n2. Sample ingestion using Windsurf:")
    print("   After inspecting the staging directory, you can ingest a batch file using:")
    print("   ```")
    print("   mcp0_ingest_data:")
    print("     data: [PASTE BATCH FILE CONTENT HERE]")
    print("     domain: python-arango-docs")
    print("   ```")
    
    print("\n3. Check database status:")
    print("   ```")
    print("   mcp0_show_databases:")
    print("   ```")

def main():
    parser = argparse.ArgumentParser(description="Demonstrate ArangoDB documentation retrieval from HADES")
    parser.add_argument("--mode", choices=['direct', 'windsurf', 'cli', 'staging', 'all'], default='all',
                        help="Mode to demonstrate: direct API, Windsurf commands, CLI, staging, or all")
    
    args = parser.parse_args()
    
    print("\n" + "*" * 80)
    print("*" + " " * 26 + "HADES ArangoDB Documentation Demo" + " " * 25 + "*")
    print("*" * 80)
    
    if args.mode in ['direct', 'all']:
        print("\n## Direct API Access")
        success = demo_direct_api()
        if not success and args.mode == 'direct':
            print("\nFallback to other methods:")
    
    if args.mode in ['windsurf', 'all'] or (args.mode == 'direct' and not success):
        print("\n## Windsurf Commands")
        demo_windsurf_commands()
    
    if args.mode in ['cli', 'all'] or (args.mode == 'direct' and not success):
        print("\n## Command Line Interface")
        demo_command_line()
    
    if args.mode in ['staging', 'all']:
        print("\n## Staging Directory and Ingestion")
        demo_staging_directory()
    
    print("\n" + "*" * 80)
    print("*" + " " * 30 + "End of Demo" + " " * 35 + "*")
    print("*" * 80 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
