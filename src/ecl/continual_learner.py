import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from ..db.connection import get_db_connection
from ..utils.versioning import KGVersion, ChangeLog

class ExternalContinualLearner:
    """
    External Continual Learner implementation for maintaining domain embeddings
    and enabling incremental updates to the knowledge graph.
    """
    
    def __init__(self, db_connection=None):
        self.logger = logging.getLogger(__name__)
        self.db = db_connection or get_db_connection()
        self.change_log = ChangeLog(self.db)
    
    def maintain_domain_embeddings(self, domain_name: str) -> Dict[str, Any]:
        """
        Update and maintain domain embeddings.
        
        Args:
            domain_name: Name of the domain to update
            
        Returns:
            Updated domain metadata
        """
        self.logger.info(f"Updating embeddings for domain: {domain_name}")
        
        # Get domain data
        domain = self._get_domain(domain_name)
        
        # Update domain embeddings
        embeddings = self._calculate_domain_embeddings(domain)
        
        # Store updated embeddings
        self._store_domain_embeddings(domain_name, embeddings)
        
        return {
            "domain": domain_name,
            "embedding_size": len(embeddings),
            "updated_at": datetime.now().isoformat()
        }
    
    def process_incremental_updates(self, start_version: str, end_version: str) -> Dict[str, Any]:
        """
        Process incremental updates based on version diffs.
        
        Args:
            start_version: Starting version string
            end_version: Ending version string
            
        Returns:
            Summary of updates processed
        """
        self.logger.info(f"Processing incremental updates from {start_version} to {end_version}")
        
        # Parse versions
        start_v = KGVersion.parse(start_version)
        end_v = KGVersion.parse(end_version)
        
        # Get changes between versions
        changes = self.change_log.get_changes_between_versions(start_v, end_v)
        
        # Count changes by type
        added_entities = [c for c in changes if c["change_type"] == "added" and c["collection"] == "entities"]
        updated_entities = [c for c in changes if c["change_type"] == "updated" and c["collection"] == "entities"]
        added_relationships = [c for c in changes if c["change_type"] == "added" and c["collection"] == "relationships"]
        
        # Process each type of change
        self._process_added_entities(added_entities)
        self._process_updated_entities(updated_entities)
        self._process_added_relationships(added_relationships)
        
        # Update affected domains
        affected_domains = self._identify_affected_domains(changes)
        for domain_name in affected_domains:
            self.maintain_domain_embeddings(domain_name)
        
        return {
            "start_version": start_version,
            "end_version": end_version,
            "changes_processed": len(changes),
            "added_entities": len(added_entities),
            "updated_entities": len(updated_entities),
            "added_relationships": len(added_relationships),
            "affected_domains": affected_domains
        }
    
    def generate_training_data(self, start_version: str, end_version: str) -> List[Dict[str, Any]]:
        """
        Generate training data from changes between versions.
        
        Args:
            start_version: Starting version string
            end_version: Ending version string
            
        Returns:
            List of training examples
        """
        self.logger.info(f"Generating training data from {start_version} to {end_version}")
        
        # Parse versions
        start_v = KGVersion.parse(start_version)
        end_v = KGVersion.parse(end_version)
        
        # Get changes between versions
        changes = self.change_log.get_changes_between_versions(start_v, end_v)
        
        # Generate training examples from changes
        training_data = []
        
        for change in changes:
            if change["collection"] == "entities" and change["change_type"] in ["added", "updated"]:
                # Create training example for entity change
                training_data.append({
                    "type": "entity_update",
                    "entity_id": change["document_id"],
                    "old_data": change.get("old_value"),
                    "new_data": change.get("new_value"),
                    "change_type": change["change_type"]
                })
            elif change["collection"] == "relationships" and change["change_type"] == "added":
                # Create training example for new relationship
                training_data.append({
                    "type": "relationship_update",
                    "relationship_id": change["document_id"],
                    "data": change.get("new_value"),
                    "change_type": change["change_type"]
                })
        
        self.logger.info(f"Generated {len(training_data)} training examples")
        return training_data
    
    def _get_domain(self, domain_name: str) -> Dict[str, Any]:
        """
        Get domain data from the database.
        
        Args:
            domain_name: Name of the domain
            
        Returns:
            Domain data
        """
        query = """
        FOR d IN domains
            FILTER d.name == @domain_name
            RETURN d
        """
        cursor = self.db.aql.execute(query, bind_vars={"domain_name": domain_name})
        domains = [doc for doc in cursor]
        
        if not domains:
            self.logger.warning(f"Domain not found: {domain_name}")
            return {"name": domain_name, "entities": []}
        
        # Get entities in the domain
        entity_query = """
        FOR d IN domains
            FILTER d.name == @domain_name
            FOR e IN OUTBOUND d entity_domains
                RETURN e
        """
        cursor = self.db.aql.execute(entity_query, bind_vars={"domain_name": domain_name})
        entities = [doc for doc in cursor]
        
        domain = domains[0]
        domain["entities"] = entities
        
        return domain
    
    def _calculate_domain_embeddings(self, domain: Dict[str, Any]) -> np.ndarray:
        """
        Calculate embeddings for a domain.
        
        Args:
            domain: Domain data including entities
            
        Returns:
            Domain embeddings
        """
        # In a real implementation, this would use ModernBERT-large or similar
        # For demonstration, creating a random embedding
        embedding_dim = 768  # Typical for BERT-large
        
        # Create a mock embedding
        embedding = np.random.randn(embedding_dim)
        embedding = embedding / np.linalg.norm(embedding)  # Normalize
        
        return embedding
    
    def _store_domain_embeddings(self, domain_name: str, embeddings: np.ndarray) -> None:
        """
        Store domain embeddings in the database.
        
        Args:
            domain_name: Name of the domain
            embeddings: Domain embeddings
        """
        # Convert numpy array to list for storage
        embedding_list = embeddings.tolist()
        
        # Store embeddings
        query = """
        FOR d IN domains
            FILTER d.name == @domain_name
            UPDATE d WITH { embeddings: @embeddings, updated_at: @timestamp } IN domains
            RETURN NEW
        """
        self.db.aql.execute(query, bind_vars={
            "domain_name": domain_name,
            "embeddings": embedding_list,
            "timestamp": datetime.now().isoformat()
        })
        
        self.logger.info(f"Stored embeddings for domain: {domain_name}")
    
    def _process_added_entities(self, added_entities: List[Dict[str, Any]]) -> None:
        """
        Process added entities.
        
        Args:
            added_entities: List of added entity changes
        """
        for change in added_entities:
            entity_id = change["document_id"]
            self.logger.info(f"Processing added entity: {entity_id}")
            
            # In a real implementation, this would update relevant indexes and models
            # For demonstration, logging only
            self.logger.info(f"Added entity processed: {entity_id}")
    
    def _process_updated_entities(self, updated_entities: List[Dict[str, Any]]) -> None:
        """
        Process updated entities.
        
        Args:
            updated_entities: List of updated entity changes
        """
        for change in updated_entities:
            entity_id = change["document_id"]
            self.logger.info(f"Processing updated entity: {entity_id}")
            
            # In a real implementation, this would update relevant indexes and models
            # For demonstration, logging only
            self.logger.info(f"Updated entity processed: {entity_id}")
    
    def _process_added_relationships(self, added_relationships: List[Dict[str, Any]]) -> None:
        """
        Process added relationships.
        
        Args:
            added_relationships: List of added relationship changes
        """
        for change in added_relationships:
            relationship_id = change["document_id"]
            self.logger.info(f"Processing added relationship: {relationship_id}")
            
            # In a real implementation, this would update relevant indexes and models
            # For demonstration, logging only
            self.logger.info(f"Added relationship processed: {relationship_id}")
    
    def _identify_affected_domains(self, changes: List[Dict[str, Any]]) -> List[str]:
        """
        Identify domains affected by changes.
        
        Args:
            changes: List of changes
            
        Returns:
            List of affected domain names
        """
        affected_domains = set()
        
        # Get entity IDs from changes
        entity_ids = []
        for change in changes:
            if change["collection"] == "entities":
                entity_ids.append(change["document_id"])
            elif change["collection"] == "relationships":
                # For relationships, need to get the connected entities
                rel_data = change.get("new_value", {})
                if "_from" in rel_data:
                    entity_ids.append(rel_data["_from"])
                if "_to" in rel_data:
                    entity_ids.append(rel_data["_to"])
        
        # Find domains containing these entities
        if entity_ids:
            query = """
            FOR e IN entities
                FILTER e._id IN @entity_ids
                FOR d IN INBOUND e entity_domains
                    RETURN DISTINCT d.name
            """
            cursor = self.db.aql.execute(query, bind_vars={"entity_ids": entity_ids})
            domains = [doc for doc in cursor]
            affected_domains.update(domains)
        
        return list(affected_domains) 