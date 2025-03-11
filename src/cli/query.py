from typing import Any, Dict, List, Optional
import logging
from src.core.orchestrator import HADESOrchestrator

logger = logging.getLogger(__name__)

class QueryCLI:
    """
    Command-line interface for querying the HADES system.
    
    This module provides a simple CLI to process queries through the HADES pipeline.
    """

    def __init__(self):
        """Initialize the QueryCLI module."""
        logger.info("Initializing QueryCLI module")
        self.orchestrator = HADESOrchestrator()
    
    def process_query(
        self,
        query: str,
        max_results: int = 5,
        domain_filter: Optional[str] = None,
        as_of_version: Optional[str] = None,
        as_of_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query through the HADES pipeline.
        
        Args:
            query: The natural language query to process
            max_results: Maximum number of results to return
            domain_filter: Optional domain to filter results by
            as_of_version: Optional version to query against
            as_of_timestamp: Optional timestamp to query against
            
        Returns:
            Dictionary containing the processed results
        """
        logger.info(f"Processing query: {query}")
        
        try:
            result = self.orchestrator.process_query(
                query=query,
                max_results=max_results,
                domain_filter=domain_filter,
                as_of_version=as_of_version,
                as_of_timestamp=as_of_timestamp
            )
            
            if not result["success"]:
                logger.warning("Query processing failed")
                return {
                    "success": False,
                    "error": result.get("error")
                }
            
            logger.info(f"Query processed successfully: {query}")
            return result
        
        except Exception as e:
            logger.exception("An error occurred while processing the query")
            return {
                "success": False,
                "error": str(e)
            }
