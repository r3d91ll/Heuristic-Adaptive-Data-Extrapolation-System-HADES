#!/usr/bin/env python3
"""
Script to ingest markdownified documentation into HADES knowledge graph
"""

import os
import sys
import argparse
import json
import glob
from pathlib import Path

def read_markdown_file(file_path):
    """Read markdown file content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def prepare_data_for_ingest(base_dir, domain="python-arango-docs"):
    """
    Prepare data for ingestion into HADES knowledge graph
    """
    data_points = []
    
    # Get all markdown files recursively
    md_files = glob.glob(os.path.join(base_dir, "**/*.md"), recursive=True)
    
    for file_path in md_files:
        # Extract title from file path - use the filename without extension
        file_name = os.path.basename(file_path)
        title = os.path.splitext(file_name)[0]
        
        # For better titles, replace underscores and hyphens with spaces and capitalize
        title = title.replace('_', ' ').replace('-', ' ').title()
        if title.lower() == "index":
            title = "Python ArangoDB Documentation"
            
        # Read the content of the markdown file
        content = read_markdown_file(file_path)
        if not content:
            continue
            
        # Create a unique ID based on the file path
        rel_path = os.path.relpath(file_path, base_dir)
        doc_id = rel_path.replace('/', '_').replace('.', '_').replace(' ', '_')
        
        # Create the data point
        data_point = {
            "id": doc_id,
            "title": title,
            "content": content,
            "source": f"file://{os.path.abspath(file_path)}",
            "metadata": {
                "type": "documentation",
                "domain": domain,
                "path": rel_path
            }
        }
        
        data_points.append(data_point)
        print(f"Prepared {rel_path} for ingestion")
    
    return data_points

def save_ingest_data(data_points, output_file):
    """Save data for ingestion to a JSON file"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_points, f, indent=2)
        print(f"Data saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving data to {output_file}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Prepare markdownified docs for HADES ingestion")
    parser.add_argument("source_dir", help="Directory containing markdown files")
    parser.add_argument("--output", default="ingest_data.json", help="Output JSON file path")
    parser.add_argument("--domain", default="python-arango-docs", help="Domain for the documentation")
    
    args = parser.parse_args()
    
    data_points = prepare_data_for_ingest(args.source_dir, args.domain)
    if not data_points:
        print("No data points to ingest")
        return 1
        
    return 0 if save_ingest_data(data_points, args.output) else 1

if __name__ == "__main__":
    sys.exit(main())
