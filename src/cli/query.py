"""
Command-line interface for querying HADES.
"""
import argparse
import json
import sys
from typing import Any, Dict, Optional

import httpx

from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def query_hades(
    query: str, max_results: int = 5, domain_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query the HADES MCP server.
    
    Args:
        query: The natural language query to send
        max_results: Maximum number of results to return
        domain_filter: Optional domain to filter results by
        
    Returns:
        The response from the HADES MCP server
    """
    mcp_url = f"http://{config.mcp.host}:{config.mcp.port}/query"
    
    # Prepare the request payload
    payload = {
        "query": query,
        "max_results": max_results
    }
    
    if domain_filter:
        payload["domain_filter"] = domain_filter
    
    try:
        # Send the request to the MCP server
        with httpx.Client(timeout=30.0) as client:
            response = client.post(mcp_url, json=payload)
            
            # Check for successful response
            response.raise_for_status()
            
            # Parse the JSON response
            return response.json()
    
    except httpx.RequestError as e:
        logger.error(f"Request to MCP server failed: {e}")
        return {
            "error": f"Failed to connect to MCP server: {e}"
        }
    
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from MCP server: {e}")
        return {
            "error": f"MCP server returned error: {e.response.status_code} - {e.response.text}"
        }
    
    except Exception as e:
        logger.error(f"Unexpected error querying HADES: {e}")
        return {
            "error": f"Unexpected error: {e}"
        }


def main() -> None:
    """Run the CLI query."""
    parser = argparse.ArgumentParser(description="Query the HADES system")
    parser.add_argument("query", help="Natural language query to process")
    parser.add_argument(
        "--max-results", type=int, default=5, help="Maximum number of results to return"
    )
    parser.add_argument(
        "--domain", help="Optional domain to filter results by"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    # Query HADES
    result = query_hades(
        query=args.query,
        max_results=args.max_results,
        domain_filter=args.domain,
    )
    
    # Check for errors
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    
    # Output the results
    if args.json:
        # Output as JSON
        print(json.dumps(result, indent=2))
    else:
        # Pretty print the results
        print("\n" + "="*80)
        print(f"Query: {args.query}")
        print("="*80 + "\n")
        
        # Print the answer
        print(f"Answer: {result.get('answer', 'No answer provided')}\n")
        
        # Print sources if available
        sources = result.get("sources", [])
        if sources:
            print("Sources:")
            for i, source in enumerate(sources, 1):
                print(f"  {i}. {source.get('title', 'Unknown')} - {source.get('url', 'No URL')}")
        
        # Print paths if available
        paths = result.get("paths", [])
        if paths:
            print("\nKnowledge Paths:")
            for i, path in enumerate(paths, 1):
                source = path.get("source", {})
                target = path.get("target", {})
                print(f"  {i}. {source.get('name', 'Unknown')} -> ... -> {target.get('name', 'Unknown')}")
                
                # Print relationships in the path
                relationships = path.get("relationships", [])
                if relationships:
                    print("     Relationships:")
                    for j, rel in enumerate(relationships, 1):
                        print(f"       {j}. {rel.get('type', 'Unknown')}")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    main()
