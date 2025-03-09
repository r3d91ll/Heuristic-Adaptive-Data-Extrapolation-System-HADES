"""
Core orchestrator for HADES.

This module ties together all HADES components into a unified pipeline:
- PathRAG for graph-based retrieval
- TCR for triple context restoration
- GraphCheck for fact verification
- ECL for continual learning
"""
from typing import Any, Dict, List, Optional

from src.db.connection import connection
from src.ecl.learner import ecl
from src.graphcheck.verification import graphcheck
from src.rag.pathrag import execute_pathrag
from src.tcr.restoration import tcr
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HADESOrchestrator:
    """
    Main orchestrator for the HADES system.
    
    This class coordinates all HADES components to process queries,
    retrieve knowledge, verify facts, and generate responses.
    """
    
    def __init__(self):
        """Initialize the HADES orchestrator."""
        logger.info("Initializing HADES orchestrator")
    
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
        
        This implements the full HADES pipeline:
        1. PathRAG retrieval identifies relevant paths in the knowledge graph
        2. TCR enriches those paths with contextual information
        3. Initial LLM response is generated (mock in Phase 1)
        4. GraphCheck verifies facts in the response
        5. ECL suggests any newly ingested relevant information
        
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
        
        # Add version info to the log if present
        if as_of_version:
            logger.info(f"Using version: {as_of_version}")
        if as_of_timestamp:
            logger.info(f"Using timestamp: {as_of_timestamp}")
        
        # Step 1: PathRAG Retrieval
        pathrag_result = execute_pathrag(
            query=query,
            max_paths=max_results,
            domain_filter=domain_filter,
            as_of_version=as_of_version,
            as_of_timestamp=as_of_timestamp
        )
        
        if not pathrag_result.get("success", False):
            logger.error(f"PathRAG retrieval failed: {pathrag_result.get('error')}")
            return {
                "success": False,
                "error": f"Retrieval failed: {pathrag_result.get('error')}",
                "query": query
            }
        
        # Step 2: TCR Enrichment (for each path)
        paths = pathrag_result.get("paths", [])
        enriched_paths = []
        
        for path in paths:
            enriched_path = tcr.restore_context_for_path(
                path, 
                as_of_version=as_of_version,
                as_of_timestamp=as_of_timestamp
            )
            enriched_paths.append(enriched_path)
        
        # Step 3: Generate initial LLM response
        # In Phase 1, we'll use a mock response
        initial_response = f"This is a placeholder response to the query: {query}"
        
        # Step 4: GraphCheck Verification
        verification_result = graphcheck.verify_text(
            initial_response,
            as_of_version=as_of_version,
            as_of_timestamp=as_of_timestamp
        )
        
        # Step 5: Query-Driven Feedback and ECL
        additional_contexts = tcr.query_driven_feedback(
            query, 
            initial_response,
            as_of_version=as_of_version,
            as_of_timestamp=as_of_timestamp
        )
        
        # When doing historical queries, we need to get documents
        # that were valid at that point in time
        relevant_documents = ecl.suggest_relevant_documents(
            query,
            limit=max_results,
            as_of_version=as_of_version
        )
        
        # Step 6: Generate final response
        # In Phase 1, we'll use a mock final response
        if verification_result.get("verification_rate", 0) > 0.8:
            final_response = initial_response
        else:
            final_response = f"I'm not confident about my answer to: {query}"
        
        # Compile the final result
        result = {
            "success": True,
            "query": query,
            "answer": final_response,
            "paths": enriched_paths,
            "verification": verification_result,
            "additional_contexts": additional_contexts,
            "relevant_documents": relevant_documents
        }
        
        # Add version info if present
        if as_of_version:
            result["version"] = as_of_version
        if as_of_timestamp:
            result["timestamp"] = as_of_timestamp
            
        return result
    
    def ingest_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest a new document into the HADES knowledge graph.
        
        Args:
            document: The document to ingest
            
        Returns:
            Status of the ingestion operation
        """
        logger.info(f"Ingesting document: {document.get('title', 'Untitled')}")
        
        # Delegate to ECL for ingestion
        ingest_result = ecl.ingest_new_document(document)
        
        # Add versioning information to the response
        if ingest_result.get("success", True):
            logger.info(f"Document ingested successfully, version: {ingest_result.get('version', 'unknown')}")
        
        return ingest_result
    
    def get_version_history(self, collection: str, document_id: str) -> Dict[str, Any]:
        """
        Get the version history of a document.
        
        Args:
            collection: Collection name
            document_id: Document ID
            
        Returns:
            Version history
        """
        logger.info(f"Getting version history for {document_id}")
        
        return connection.get_document_history(collection, document_id)
    
    def compare_versions(
        self, 
        collection: str, 
        document_id: str, 
        version1: str, 
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two versions of a document.
        
        Args:
            collection: Collection name
            document_id: Document ID
            version1: First version to compare
            version2: Second version to compare
            
        Returns:
            Difference between versions
        """
        logger.info(f"Comparing versions {version1} and {version2} for {document_id}")
        
        return connection.compare_versions(
            collection=collection,
            document_id=document_id,
            version1=version1,
            version2=version2
        )


# Create a global instance
orchestrator = HADESOrchestrator()
