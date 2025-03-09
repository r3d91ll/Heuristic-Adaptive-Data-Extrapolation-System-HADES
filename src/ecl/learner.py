"""
External Continual Learner (ECL) module for HADES.

This module implements ECL based on the research paper:
"In-context Continual Learning Assisted by an External Continual Learner"
https://arxiv.org/html/2412.15563v1
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set

from src.db.connection import connection
from src.utils.logger import get_logger
from src.utils.versioning import KGVersion, VersionMetadata, ChangeLog

logger = get_logger(__name__)


class ExternalContinualLearner:
    """
    External Continual Learner implementation.
    
    ECL maintains domain embeddings and incrementally updates them
    as new data is ingested, without requiring retraining of the main LLM.
    """
    
    def __init__(self):
        """Initialize the ECL module."""
        # In a full implementation, we would initialize embedding models here
        logger.info("Initializing External Continual Learner module")
        
        # Track the latest version we've processed for training
        self.latest_processed_version = "v0.0.0"
    
    def update_domain_embeddings(
        self, 
        domain: str, 
        documents: List[Dict[str, Any]],
        incremental: bool = True
    ) -> Dict[str, Any]:
        """
        Update domain embeddings with new documents.
        
        Args:
            domain: Domain to update
            documents: List of new documents
            incremental: Whether to do an incremental update (vs. full retraining)
            
        Returns:
            Status of the update operation
        """
        # This is a stub implementation for Phase 1
        # In a full implementation, this would use ModernBERT-large embeddings
        logger.info(f"Updating domain embeddings for {domain} with {len(documents)} documents")
        
        if incremental:
            logger.info("Performing incremental update of domain embeddings")
            
            # Get the current domain embeddings (if any)
            domain_query = """
            FOR domain IN domains
                FILTER domain.name == @domain_name AND domain.valid_until == null
                RETURN domain
            """
            domain_result = connection.execute_query(
                domain_query,
                bind_vars={"domain_name": domain}
            )
            
            if not domain_result.get("success", False) or not domain_result.get("result"):
                logger.warning(f"Domain {domain} not found, creating new domain")
                return self._create_new_domain(domain, documents)
            
            # Get the current domain document
            domain_doc = domain_result.get("result")[0]
            
            # In a real implementation, we would:
            # 1. Compute embeddings for each document
            # 2. Update the Gaussian mixture for the domain incrementally
            # 3. Store the updated embeddings in the database
            
            # For now, we'll just create a new version of the domain
            # with a mock update
            domain_id = domain_doc.get("_id", "").split("/")[1]  # Get just the key part
            
            # Create a new version of the domain document
            updated_domain = domain_doc.copy()
            updated_domain["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated_domain["document_count"] = domain_doc.get("document_count", 0) + len(documents)
            updated_domain["last_document_titles"] = [doc.get("title", "Untitled") for doc in documents[:5]]
            
            # Update the domain document with versioning
            update_result = connection.update_document(
                collection="domains",
                document_key=domain_id,
                update_data=updated_domain,
                versioned=True
            )
            
            if not update_result.get("success", False):
                logger.error(f"Failed to update domain: {update_result.get('error')}")
                return {
                    "success": False,
                    "error": update_result.get("error")
                }
            
            return {
                "success": True,
                "domain": domain,
                "documents_processed": len(documents),
                "message": "Domain embeddings updated incrementally"
            }
        else:
            # Full retraining
            logger.info("Performing full retraining of domain embeddings")
            
            # In a real implementation, we would:
            # 1. Compute embeddings for all documents in the domain
            # 2. Create a new Gaussian mixture model
            # 3. Replace the existing embedding model
            
            return {
                "success": True,
                "domain": domain,
                "documents_processed": len(documents),
                "message": "Domain embeddings fully retrained (stub implementation)"
            }
    
    def _create_new_domain(self, domain: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a new domain with the given documents.
        
        Args:
            domain: Domain name
            documents: List of documents to initialize the domain with
            
        Returns:
            Status of the creation operation
        """
        try:
            # Create a domain document
            domain_doc = {
                "name": domain,
                "document_count": len(documents),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_document_titles": [doc.get("title", "Untitled") for doc in documents[:5]],
                # In a real implementation, we would include Gaussian parameters here
            }
            
            # Insert with versioning
            insert_result = connection.insert_document(
                collection="domains",
                document=domain_doc,
                versioned=True
            )
            
            if not insert_result.get("success", False):
                logger.error(f"Failed to create domain: {insert_result.get('error')}")
                return {
                    "success": False,
                    "error": insert_result.get("error")
                }
            
            return {
                "success": True,
                "domain": domain,
                "documents_processed": len(documents),
                "message": "New domain created with embeddings"
            }
        except Exception as e:
            logger.error(f"Error creating domain: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def calculate_domain_relevance(
        self, query: str, domains: Optional[List[str]] = None,
        as_of_version: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Calculate relevance scores of a query to different domains.
        
        Args:
            query: The query to evaluate
            domains: Optional list of domains to check; if None, check all domains
            as_of_version: Optional version to use for historical queries
            
        Returns:
            Dictionary mapping domain names to relevance scores
        """
        # In Phase 1, this is a stub implementation
        # In a full implementation, this would use Mahalanobis distance
        logger.info(f"Calculating domain relevance for query: {query}")
        
        # Get all domains if not specified
        if domains is None:
            aql_query = """
            FOR domain IN domains
                FILTER domain.valid_until == null
                RETURN domain.name
            """
            
            # If using a specific version
            if as_of_version:
                result = connection.execute_query(
                    aql_query,
                    as_of_version=as_of_version
                )
            else:
                result = connection.execute_query(aql_query)
                
            if result["success"]:
                domains = [d for d in result.get("result", [])]
            else:
                logger.error(f"Failed to retrieve domains: {result.get('error')}")
                return {}
        
        # In a real implementation, we would:
        # 1. Compute embedding for the query
        # 2. Calculate Mahalanobis distance to each domain's Gaussian
        # 3. Convert distances to relevance scores
        
        # For now, return random scores
        import random
        return {domain: random.random() for domain in domains}
    
    def ingest_new_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest a new document into the knowledge graph.
        
        Args:
            document: The document to ingest
            
        Returns:
            Status of the ingestion operation
        """
        logger.info(f"Ingesting new document: {document.get('title', 'Untitled')}")
        
        try:
            # Extract basic document metadata
            title = document.get("title", "Untitled")
            content = document.get("content", "")
            domain = document.get("domain", "general")
            
            # In a real implementation, we would:
            # 1. Extract entities and relationships from the document
            # 2. Add them to the knowledge graph with version metadata
            # 3. Update domain embeddings
            
            # For now, we'll create a simple entity for the document
            doc_entity = {
                "name": title,
                "type": "document",
                "content": content,
                "domain": domain,
                "ingestion_date": datetime.now(timezone.utc).isoformat(),
                "properties": {
                    "word_count": len(content.split()),
                    "source": document.get("source", "unknown")
                }
            }
            
            # Insert with versioning
            entity_result = connection.insert_document(
                collection="entities",
                document=doc_entity,
                versioned=True
            )
            
            if not entity_result.get("success", False):
                logger.error(f"Failed to insert document entity: {entity_result.get('error')}")
                return {
                    "success": False,
                    "error": entity_result.get("error")
                }
            
            # Get the new entity ID
            entity_id = entity_result.get("result", {}).get("_id")
            
            # Update domain embeddings (incremental update)
            self.update_domain_embeddings(domain, [document])
            
            # Get the current version to mark for processed
            entity_doc = entity_result.get("result", {})
            current_version = entity_doc.get("version", "v0.1.0")
            
            # Update our latest processed version if this is newer
            if KGVersion.compare_versions(current_version, self.latest_processed_version) > 0:
                self.latest_processed_version = current_version
            
            return {
                "success": True,
                "document_id": entity_id,
                "version": current_version,
                "message": "Document ingested successfully"
            }
            
        except Exception as e:
            logger.error(f"Error ingesting document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def suggest_relevant_documents(
        self, 
        query: str, 
        limit: int = 5,
        as_of_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest relevant documents for a query based on domain relevance.
        
        Args:
            query: The query to find documents for
            limit: Maximum number of documents to return
            as_of_version: Optional version to use for historical queries
            
        Returns:
            List of relevant documents
        """
        logger.info(f"Finding relevant documents for query: {query}")
        
        # Calculate domain relevance
        domain_scores = self.calculate_domain_relevance(
            query, 
            as_of_version=as_of_version
        )
        
        # Sort domains by relevance
        sorted_domains = sorted(
            domain_scores.items(), key=lambda x: x[1], reverse=True
        )
        
        # In a real implementation, we would search for documents based on embedding similarity
        # For now, we'll just query ArangoDB for documents in the most relevant domains
        documents = []
        for domain, score in sorted_domains:
            # Query for documents in this domain
            doc_query = """
            FOR entity IN entities
                FILTER 
                    entity.type == "document" AND 
                    entity.domain == @domain AND
                    entity.valid_until == null
                SORT RAND() // Random sort for now, would be embedding similarity in real impl
                LIMIT @limit
                RETURN {
                    "id": entity._id,
                    "title": entity.name,
                    "domain": entity.domain,
                    "relevance": @score,
                    "version": entity.version,
                    "summary": SUBSTRING(entity.content, 0, 150) + "..."
                }
            """
            
            # Execute with versioning if specified
            if as_of_version:
                doc_result = connection.execute_query(
                    doc_query,
                    bind_vars={"domain": domain, "score": score, "limit": limit - len(documents)},
                    as_of_version=as_of_version
                )
            else:
                doc_result = connection.execute_query(
                    doc_query,
                    bind_vars={"domain": domain, "score": score, "limit": limit - len(documents)}
                )
            
            if doc_result.get("success", False):
                domain_docs = doc_result.get("result", [])
                documents.extend(domain_docs)
                
                if len(documents) >= limit:
                    break
        
        # If we didn't find any actual documents, return placeholders
        if not documents:
            for domain, score in sorted_domains[:limit]:
                documents.append({
                    "title": f"Document about {domain}",
                    "domain": domain,
                    "relevance": score,
                    "summary": f"This is a placeholder document about {domain}."
                })
        
        return documents
    
    def process_unprocessed_changes(self) -> Dict[str, Any]:
        """
        Process any changes that haven't been incorporated into training data.
        
        This method identifies changes since the last processed version,
        generates training examples, and updates the latest processed version.
        
        Returns:
            Status of the operation
        """
        logger.info(f"Processing changes since version {self.latest_processed_version}")
        
        try:
            # Get the most recent version in the system
            version_query = """
            FOR log IN change_logs
                SORT log.timestamp DESC
                LIMIT 1
                RETURN log.new_version
            """
            
            version_result = connection.execute_query(version_query)
            
            if not version_result.get("success", False) or not version_result.get("result"):
                logger.warning("No changes found to process")
                return {
                    "success": True,
                    "message": "No changes found to process"
                }
            
            latest_version = version_result.get("result")[0]
            
            # If we're already at the latest version, nothing to do
            if KGVersion.compare_versions(latest_version, self.latest_processed_version) <= 0:
                logger.info("Already at the latest version")
                return {
                    "success": True,
                    "message": "Already at the latest version"
                }
            
            # Import here to avoid circular imports
            from src.utils.version_sync import version_sync
            
            # Generate training data from the diff
            result = version_sync.generate_training_data_from_diff(
                start_version=self.latest_processed_version,
                end_version=latest_version,
                output_file=f"training_data_{self.latest_processed_version}_to_{latest_version}.json"
            )
            
            if not result.get("success", False):
                logger.error(f"Failed to generate training data: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error")
                }
            
            # Update the latest processed version
            self.latest_processed_version = latest_version
            
            return {
                "success": True,
                "previous_version": result.get("versions", {}).get("start"),
                "new_version": result.get("versions", {}).get("end"),
                "training_examples": result.get("training_examples", 0),
                "message": "Successfully processed changes and generated training data"
            }
            
        except Exception as e:
            logger.error(f"Error processing changes: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Create a global instance
ecl = ExternalContinualLearner()
