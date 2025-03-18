"""
ArangoDB Connection Patch Module

This module contains patches and utilities for handling ArangoDB connections
to ensure proper URL scheme handling throughout all API calls.
"""

import logging
from typing import Optional, Dict, Any, Union, List
import os
from urllib.parse import urlparse, urlunparse
from arango import ArangoClient

# Configure logger
logger = logging.getLogger(__name__)

class PatchedArangoClient(ArangoClient):
    """
    A patched version of ArangoClient that ensures proper URL scheme handling.
    This class extends the standard ArangoClient to fix issues with URL schemes
    being dropped during internal operations.
    """
    
    def __init__(self, hosts="http://localhost:8529", **kwargs):
        """
        Initialize the patched ArangoClient with proper URL handling.
        
        Args:
            hosts: ArangoDB host URL(s)
            **kwargs: Additional arguments to pass to ArangoClient
        """
        # Ensure host has proper scheme
        parsed_hosts = []
        if isinstance(hosts, str):
            hosts = [hosts]
            
        for host in hosts:
            parsed = urlparse(host)
            # Add scheme if missing
            if not parsed.scheme:
                parsed = parsed._replace(scheme='http')
            # Ensure netloc is present
            if not parsed.netloc and parsed.path:
                # Assume the path is actually the netloc
                parsed = parsed._replace(netloc=parsed.path, path='')
            # Add port if missing
            if ':' not in parsed.netloc:
                parsed = parsed._replace(netloc=f"{parsed.netloc}:8529")
            parsed_hosts.append(urlunparse(parsed))
        
        logger.info(f"Initializing PatchedArangoClient with hosts: {parsed_hosts}")
        # Call the parent constructor with the fixed URLs
        super().__init__(hosts=parsed_hosts[0] if len(parsed_hosts) == 1 else parsed_hosts, **kwargs)

def get_patched_arango_client(host: str = None, **kwargs) -> PatchedArangoClient:
    """
    Get a patched ArangoDB client with proper URL scheme handling.
    
    Args:
        host: ArangoDB host URL (optional, default from environment)
        **kwargs: Additional arguments to pass to ArangoClient
        
    Returns:
        PatchedArangoClient instance
    """
    if host is None:
        arango_host = os.environ.get("HADES_ARANGO_HOST", "localhost")
        arango_port = os.environ.get("HADES_ARANGO_PORT", "8529")
        host = f"http://{arango_host}:{arango_port}"
    
    return PatchedArangoClient(hosts=host, **kwargs)
