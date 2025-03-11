from typing import Any, Dict, List, Optional
import spacy
from src.db.connection import DBConnection
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TripleContextRestoration:
    """
    Triple Context Restoration (TCR) implementation.
    
    TCR restores the full textual context around graph triples to enrich the knowledge graph.
    """

    def __init__(self):
        """Initialize the TCR module."""
        logger.info("Initializing TripleContextRestoration module")
        self.nlp = spacy.load("en_core_web_md")
        self.db_connection = DBConnection()

    def restore_context_for_path(
        self,
        paths: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Restore context for a list of paths.
        
        Args:
            paths: List of paths to restore context for
            
        Returns:
            Restored context and response
        """
        logger.info(f"Restoring context for {len(paths)} paths")
        
        try:
            restored_context = []
            
            for path in paths:
                # Extract triples from the path
                triples = self._extract_triples(path)
                
                if not triples:
                    logger.warning(f"No triples extracted for path: {path}")
                    continue
                
                # Restore context for each triple
                for triple in triples:
                    restored_context.append(self._restore_context_for_triple(triple))
            
            return {
                "success": True,
                "paths": paths,
                "restored_context": restored_context
            }
        
        except Exception as e:
            logger.exception("An error occurred while restoring context")
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_triples(self, path: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract triples from a given path.
        
        Args:
            path: The path to extract triples from
            
        Returns:
            List of extracted triples
        """
        # Placeholder for triple extraction logic
        try:
            # Example: Using a simple placeholder model
            triples = []
            
            for node in path.get("nodes", []):
                if "subject" in node and "predicate" in node and "object" in node:
                    triples.append({
                        "subject": node["subject"],
                        "predicate": node["predicate"],
                        "object": node["object"]
                    })
            
            return triples
        
        except Exception as e:
            logger.exception("An error occurred while extracting triples")
            raise e

    def _restore_context_for_triple(self, triple: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore context for a single triple.
        
        Args:
            triple: The triple to restore context for
            
        Returns:
            Restored context for the triple
        """
        # Placeholder for context restoration logic
        try:
            # Example: Using spaCy's en_core_web_md model for context restoration
            subject = triple["subject"]
            predicate = triple["predicate"]
            obj = triple["object"]
            
            # Generate a query to fetch related documents from the knowledge graph
            aql_query = f"""
            FOR doc IN entities
                FILTER doc.name == @subject OR doc.name == @obj
                RETURN {{
                    "text": doc.text,
                    "metadata": doc.metadata
                }}
            """
            
            bind_vars = {
                "subject": subject,
                "obj": obj
            }
            
            result = self.db_connection.execute_query(aql_query, bind_vars=bind_vars)
            
            if not result["success"]:
                logger.error(f"Context restoration failed: {result.get('error')}")
                return {
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "text": "",
                    "metadata": {}
                }
            
            documents = result["result"]
            
            if not documents:
                logger.warning(f"No documents found for triple: {triple}")
                return {
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "text": "",
                    "metadata": {}
                }
            
            # Combine document texts to form the context
            context_text = " ".join(doc.get("text", "") for doc in documents)
            
            if not context_text:
                logger.warning(f"No context text found for triple: {triple}")
                return {
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "text": "",
                    "metadata": {}
                }
            
            # Process the combined text using spaCy to extract relevant sentences
            doc = self.nlp(context_text)
            
            # Extract sentences containing the subject and object
            relevant_sentences = []
            for sent in doc.sents:
                if subject.lower() in sent.text.lower() or obj.lower() in sent.text.lower():
                    relevant_sentences.append(sent.text.strip())
            
            context = {
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "text": "\n".join(relevant_sentences),
                "metadata": {doc["name"]: doc.get("metadata", {}) for doc in documents}
            }
            
            logger.info(f"Context restored for triple: {triple}")
            return context
        
        except Exception as e:
            logger.exception("An error occurred while restoring context for triple")
            raise e
