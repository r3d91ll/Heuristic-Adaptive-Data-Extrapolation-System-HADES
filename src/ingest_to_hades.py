#!/usr/bin/env python3
"""
Script to ingest prepared data into the HADES knowledge graph
"""

import os
import sys
import argparse
import json
import requests

def load_ingest_data(json_file):
    """Load data from a JSON file"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading data from {json_file}: {e}")
        return None

def ingest_data_to_hades(data_points, domain="python-arango-docs", batch_size=5):
    """
    Ingest data into the HADES knowledge graph using the MCP API
    """
    # For using MCP directly in Windsurf, we'll use another approach
    # Instead, we'll save the batches and provide instructions to use the MCP tool
    
    total = len(data_points)
    batches = [data_points[i:i+batch_size] for i in range(0, total, batch_size)]
    
    print(f"Prepared {total} data points in {len(batches)} batches for ingestion")
    
    # Save batches to individual files for easier ingestion
    batch_files = []
    for i, batch in enumerate(batches, 1):
        batch_file = f"batch_{i}_of_{len(batches)}.json"
        with open(batch_file, 'w', encoding='utf-8') as f:
            json.dump(batch, f, indent=2)
        batch_files.append(batch_file)
        print(f"Saved batch {i}/{len(batches)} to {batch_file}")
    
    print(f"\nTo ingest these batches into HADES, use the 'ingest_data' MCP tool for each batch file.")
    print(f"Example: Ingest the first batch using:\n")
    print(f"  data: <contents of {batch_files[0]}>")
    print(f"  domain: {domain}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Ingest data into HADES knowledge graph")
    parser.add_argument("json_file", help="JSON file containing data to ingest")
    parser.add_argument("--domain", default="python-arango-docs", help="Domain for the documentation")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of items to ingest in each batch")
    
    args = parser.parse_args()
    
    data_points = load_ingest_data(args.json_file)
    if not data_points:
        print("No data points to ingest")
        return 1
    
    success = ingest_data_to_hades(data_points, args.domain, args.batch_size)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
