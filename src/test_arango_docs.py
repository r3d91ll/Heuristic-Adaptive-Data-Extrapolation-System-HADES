#!/usr/bin/env python3
"""
Script to test the retrieval of ArangoDB documentation from HADES knowledge graph
"""

import os
import sys
import json
import argparse
from pathlib import Path
import subprocess
import glob

def inspect_staging_directory(domain="python-arango-docs"):
    """
    Inspect the staging directory for a specific domain and provide a summary of batch files
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Standardize domain name for directory structure
    domain_safe = domain.replace('-', '_').replace(' ', '_').lower()
    staging_dir = os.path.join(project_root, 'data', 'staging', domain_safe)
    
    if not os.path.exists(staging_dir):
        print(f"Staging directory not found: {staging_dir}")
        return None
    
    print(f"Inspecting staging directory: {staging_dir}")
    print("-" * 80)
    
    # Check for manifest file
    manifest_file = os.path.join(staging_dir, "manifest.json")
    manifest_data = None
    
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            print("Found manifest file:")
            print(f"  Domain: {manifest_data.get('domain')}")
            print(f"  Total documents: {manifest_data.get('total_documents')}")
            print(f"  Batch size: {manifest_data.get('batch_size')}")
            print(f"  Number of batches: {manifest_data.get('num_batches')}")
            print(f"  Timestamp: {manifest_data.get('timestamp')}")
        except Exception as e:
            print(f"Error reading manifest file: {e}")
    else:
        print("No manifest file found.")
    
    # Find all batch files
    batch_files = glob.glob(os.path.join(staging_dir, "batch_*.json"))
    batch_files.sort()
    
    if not batch_files:
        print("No batch files found in the staging directory.")
        return None
    
    print(f"\nFound {len(batch_files)} batch files:")
    
    total_docs = 0
    for batch_file in batch_files:
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
                doc_count = len(batch_data)
                total_docs += doc_count
                print(f"  {os.path.basename(batch_file)}: {doc_count} documents")
                
                # Print the first document's ID to help with verification
                if doc_count > 0:
                    print(f"    First doc ID: {batch_data[0].get('id', 'unknown')}")
        except Exception as e:
            print(f"  {os.path.basename(batch_file)}: Error reading file - {e}")
    
    print(f"\nTotal documents across all batch files: {total_docs}")
    
    # Provide instructions for ingestion
    print("\nTo ingest these batches into HADES, use the following commands:")
    print("1. In Windsurf, use the 'mcp0_ingest_data' tool with the content of each batch file")
    print(f"2. Set the domain parameter to '{domain}'")
    print("\nExample for the first batch (if available):")
    if batch_files:
        print(f"   - Open the file: {batch_files[0]}")
        print("   - Copy the content")
        print("   - Use the following in Windsurf:")
        print("     ```")
        print("     mcp0_ingest_data:")
        print("       data: [PASTE CONTENT HERE]")
        print(f"       domain: {domain}")
        print("     ```")
    
    return {
        "staging_dir": staging_dir,
        "manifest": manifest_data,
        "batch_files": batch_files,
        "total_docs": total_docs
    }


def test_knowledge_graph_retrieval(query, domain="python-arango-docs", max_paths=5):
    """
    Test the retrieval of data from the HADES knowledge graph using the CLI tool
    """
    print(f"Query: {query}")
    print(f"Domain filter: {domain}")
    print(f"Max paths: {max_paths}")
    
    # For testing within Windsurf, write a script that demonstrates the query for the USER
    print("\nTo retrieve this information from HADES via Windsurf, use the following:")
    print("1. In Windsurf, use the 'mcp0_pathrag_retrieve' tool with the following parameters:")
    print(f"   - query: '{query}'")
    print(f"   - domain_filter: '{domain}'")
    print(f"   - max_paths: {max_paths}")
    
    # Try to run the HADES MCP server directly
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        mcp_path = os.path.join(script_dir, "mcp", "server.py")
        
        if os.path.exists(mcp_path):
            print("\nTrying to retrieve from local MCP server...")
            # Use subprocess to run the query via the CLI
            cmd = [
                sys.executable, "-c",
                f"from src.mcp.clients.pathrag import PathRAGClient; "
                f"client = PathRAGClient(); "
                f"result = client.retrieve_paths('{query}', domain_filter='{domain}', max_paths={max_paths}); "
                f"print(result)"
            ]
            
            result = subprocess.run(cmd, cwd=os.path.dirname(script_dir), 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("\nResult:")
                print(result.stdout)
                try:
                    return json.loads(result.stdout)
                except:
                    return {"success": True, "paths": []}
            else:
                print(f"\nError: {result.stderr}")
                return None
        else:
            print(f"\nCould not find MCP server at {mcp_path}")
            return None
    except Exception as e:
        print(f"\nException: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Test ArangoDB documentation retrieval from HADES")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Retrieval testing command
    retrieve_parser = subparsers.add_parser("retrieve", help="Test document retrieval from HADES")
    retrieve_parser.add_argument("--query", default="How to create a collection in ArangoDB using Python?", 
                        help="Query to test retrieval")
    retrieve_parser.add_argument("--domain", default="python-arango-docs", 
                        help="Domain to filter by")
    retrieve_parser.add_argument("--max-paths", type=int, default=5, 
                        help="Maximum number of paths to retrieve")
    retrieve_parser.add_argument("--all-queries", action="store_true",
                        help="Run all predefined test queries")
    
    # Staging directory inspection command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect staging directory for batch files")
    inspect_parser.add_argument("--domain", default="python-arango-docs", 
                        help="Domain name for staging directory")
    
    # Help as default
    if len(sys.argv) == 1:
        parser.print_help()
        return 1
    
    args = parser.parse_args()
    
    if args.command == "retrieve":
        # Test queries related to ArangoDB Python client
        if args.all_queries:
            test_queries = [
                args.query,
                "How to execute an AQL query in Python?",
                "What is a graph in ArangoDB?",
                "How to create indexes in ArangoDB using Python?",
                "How to perform transactions in ArangoDB?"
            ]
        else:
            test_queries = [args.query]
        
        print(f"Testing retrieval from HADES knowledge graph for domain: {args.domain}")
        print("-" * 80)
        
        for query in test_queries:
            print("\n" + "=" * 80)
            test_knowledge_graph_retrieval(query, args.domain, args.max_paths)
            print("=" * 80)
    
    elif args.command == "inspect":
        # Inspect staging directory
        inspect_staging_directory(args.domain)
        
    else:
        parser.print_help()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
