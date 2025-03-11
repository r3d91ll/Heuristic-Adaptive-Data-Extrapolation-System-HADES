from typing import Any, Dict, List, Optional
import logging
from src.rag.path_rag import PathRAG
from src.tcr.restoration import TripleContextRestoration
from src.graphcheck.verification import GraphCheck
from src.ecl.learner import ExternalContinualLearner

logger = logging.getLogger(__name__)

class HADESOrchestrator:
    """
    Main orchestrator for the HADES system.
    
    This class coordinates all HADES components to process queries,
    retrieve knowledge, verify facts, and generate responses.
    """

    def __init__(self):
        """Initialize the HADES orchestrator."""
        logger.info("Initializing HADES orchestrator")
        self.path_rag = PathRAG()
        self.tcr = TripleContextRestoration()
        self.graph_check = GraphCheck()
        self.ecl = ExternalContinualLearner()

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
        
        try:
            # Step 1: Retrieve paths using PathRAG
            path_rag_result = self.path_rag.retrieve_paths(
                query=query,
                max_paths=max_results,
                domain_filter=domain_filter,
                as_of_version=as_of_version,
                as_of_timestamp=as_of_timestamp
            )
            
            if not path_rag_result["success"]:
                logger.warning("No paths retrieved for the query")
                return {
                    "success": False,
                    "error": "No paths retrieved"
                }
            
            paths = path_rag_result.get("paths", [])
            logger.info(f"Retrieved {len(paths)} paths for query: {query}")
            
            # Step 2: Restore context using TCR
            tcr_result = self.tcr.restore_context_for_path(paths)
            
            if not tcr_result["success"]:
                logger.warning("Context restoration failed")
                return {
                    "success": False,
                    "error": tcr_result.get("error")
                }
            
            restored_context = tcr_result.get("restored_context", [])
            logger.info(f"Restored context for {len(restored_context)} triples")
            
            # Step 3: Verify response using GraphCheck
            verification_results = self.graph_check.verify_claims(
                claims=[{"text": rc["text"]} for rc in restored_context],
                as_of_version=as_of_version,
                as_of_timestamp=as_of_timestamp
            )
            
            if not verification_results.get("success"):
                logger.warning("Response verification failed")
                return {
                    "success": False,
                    "error": verification_results.get("error")
                }
            
            verified_claims = verification_results.get("claims", [])
            logger.info(f"Verified {len(verified_claims)} claims")
            
            # Step 4: Update embeddings using ECL if necessary
            ecl_result = self.ecl.update_embeddings(
                domain=domain_filter or "default",
                documents=[{"text": rc["text"]} for rc in restored_context],
                incremental=True
            )
            
            if not ecl_result["success"]:
                logger.warning("Embedding update failed")
                return {
                    "success": False,
                    "error": ecl_result.get("error")
                }
            
            logger.info(f"Updated embeddings for domain: {domain_filter or 'default'}")
            
            # Construct the final response
            response = {
                "query": query,
                "domain_filter": domain_filter,
                "as_of_version": as_of_version,
                "as_of_timestamp": as_of_timestamp,
                "response": [claim["claim"] for claim in verified_claims],
                "verified_claims": verified_claims
            }
            
            logger.info(f"Processed query: {query}")
            return {
                "success": True,
                **response
            }
        
        except Exception as e:
            logger.exception("An error occurred while processing the query")
            return {
                "success": False,
                "error": str(e)
            }
