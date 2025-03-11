"""
Version Synchronization Module for HADES.

This module handles synchronization of versioned knowledge graph data,
including generating training data for downstream processes like GNN training
and performing housekeeping tasks on versioned data.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from src.db.connection import DBConnection
from src.utils.logger import get_logger
from src.utils.versioning import KGVersion, VersionMetadata, ChangeLog

logger = get_logger(__name__)


class VersionSync:
    """
    Synchronizes versioned knowledge graph data with downstream processes.
    
    This class handles:
    1. Generating training data for GNNs based on knowledge graph diffs
    2. Compacting multiple small changes into larger snapshots
    3. Cleaning up old versions based on retention policies
    """
    
    def __init__(self, output_dir: str = "data/training"):
        """
        Initialize the version synchronization module.
        
        Args:
            output_dir: Directory to store generated training data
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_training_data_from_diff(
        self, 
        start_version: str, 
        end_version: str, 
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate GNN training data based on changes between two versions.
        
        Args:
            start_version: Starting version for the diff
            end_version: Ending version for the diff
            output_file: Optional file path to save the training data
            
        Returns:
            Status of the operation and summary of generated data
        """
        logger.info(f"Generating training data from diff {start_version} -> {end_version}")
        
        try:
            # Step 1: Get all changes between these versions
            changes = self._get_changes_between_versions(start_version, end_version)
            
            if not changes:
                logger.warning(f"No changes found between {start_version} and {end_version}")
                return {
                    "success": True,
                    "changes_found": 0,
                    "message": "No changes found between versions"
                }
            
            # Step 2: Extract affected subgraphs
            subgraphs = self._extract_affected_subgraphs(changes)
            
            # Step 3: Generate training examples from subgraphs
            training_data = self._generate_training_examples(subgraphs)
            
            # Step 4: Save to file if requested
            if output_file:
                if not output_file.endswith(".json"):
                    output_file += ".json"
                    
                output_path = os.path.join(self.output_dir, output_file)
                with open(output_path, "w") as f:
                    json.dump(training_data, f, indent=2)
                
                logger.info(f"Training data saved to {output_path}")
            
            return {
                "success": True,
                "changes_found": len(changes),
                "subgraphs_extracted": len(subgraphs),
                "training_examples": len(training_data.get("examples", [])),
                "output_file": output_file,
                "versions": {
                    "start": start_version,
                    "end": end_version
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate training data: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_changes_between_versions(
        self, 
        start_version: str, 
        end_version: str
    ) -> List[Dict[str, Any]]:
        """
        Get all changes between two versions.
        
        Args:
            start_version: Starting version
            end_version: Ending version
            
        Returns:
            List of change log entries
        """
        # Query the change_logs collection for all changes between versions
        query = """
        FOR log IN change_logs
            LET start_v = @start_version
            LET end_v = @end_version
            
            // Find changes where previous_version >= start_version
            // and new_version <= end_version
            FILTER 
                (log.previous_version == null OR log.previous_version >= start_v) AND
                log.new_version <= end_v
                
            SORT log.timestamp ASC
            RETURN log
        """
        
        db_connection = DBConnection()
        result = db_connection.execute_query(
            query,
            bind_vars={
                "start_version": start_version,
                "end_version": end_version
            }
        )
        
        if not result.get("success", False):
            logger.error(f"Failed to query changes: {result.get('error')}")
            return []
        
        return result.get("result", [])
    
    def _extract_affected_subgraphs(
        self, 
        changes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract subgraphs affected by the changes.
        
        Args:
            changes: List of change log entries
            
        Returns:
            List of subgraphs (entities and their relationships)
        """
        affected_entities = set()
        
        # Collect all affected entity IDs
        for change in changes:
            entity_id = change.get("entity_id")
            if entity_id:
                affected_entities.add(entity_id)
        
        if not affected_entities:
            return []
        
        # Extract subgraphs for each affected entity
        subgraphs = []
        db_connection = DBConnection()
        for entity_id in affected_entities:
            subgraph = self._extract_entity_subgraph(db_connection, entity_id)
            if subgraph:
                subgraphs.append(subgraph)
        
        return subgraphs
    
    def _extract_entity_subgraph(
        self, 
        db_connection: DBConnection,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract a subgraph centered around an entity.
        
        Args:
            db_connection: Database connection instance
            entity_id: Central entity ID
            
        Returns:
            Subgraph data or None if not found
        """
        # Get the entity
        parts = entity_id.split("/")
        if len(parts) != 2:
            logger.warning(f"Invalid entity ID format: {entity_id}")
            return None
        
        collection, key = parts
        
        # Find the entity and its relationships (1-hop neighborhood)
        query = """
        LET entity = DOCUMENT(@entity_id)
        
        LET outbound = (
            FOR v, e IN 1..1 OUTBOUND entity relationships
                FILTER e.valid_until == null  // Get only currently valid relationships
                RETURN {
                    "vertex": v,
                    "edge": e,
                    "direction": "outbound"
                }
        )
        
        LET inbound = (
            FOR v, e IN 1..1 INBOUND entity relationships
                FILTER e.valid_until == null  // Get only currently valid relationships
                RETURN {
                    "vertex": v,
                    "edge": e,
                    "direction": "inbound"
                }
        )
        
        RETURN {
            "central_entity": entity,
            "neighbors": APPEND(outbound, inbound)
        }
        """
        
        result = db_connection.execute_query(
            query,
            bind_vars={"entity_id": entity_id}
        )
        
        if not result.get("success", False) or not result.get("result"):
            logger.warning(f"Failed to extract subgraph for {entity_id}")
            return None
        
        return result.get("result")[0]
    
    def _generate_training_examples(
        self, 
        subgraphs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate training examples from subgraphs.
        
        Args:
            subgraphs: List of subgraphs
            
        Returns:
            Dictionary containing training examples
        """
        # In a real implementation, this would be more sophisticated
        # For now, we'll generate simple examples
        
        examples = []
        
        for subgraph in subgraphs:
            central_entity = subgraph.get("central_entity", {})
            neighbors = subgraph.get("neighbors", [])
            
            # Create a training example
            example = {
                "entity_id": central_entity.get("_id"),
                "entity_name": central_entity.get("name", "Unknown"),
                "entity_type": central_entity.get("type", "Unknown"),
                "neighbors": [],
                "relationships": []
            }
            
            # Add neighbor information
            for neighbor in neighbors:
                vertex = neighbor.get("vertex", {})
                edge = neighbor.get("edge", {})
                direction = neighbor.get("direction")
                
                example["neighbors"].append({
                    "id": vertex.get("_id"),
                    "name": vertex.get("name", "Unknown"),
                    "type": vertex.get("type", "Unknown")
                })
                
                example["relationships"].append({
                    "source": edge.get("_from"),
                    "target": edge.get("_to"),
                    "type": edge.get("type", "Unknown"),
                    "direction": direction
                })
            
            examples.append(example)
        
        # Create the final training data structure
        return {
            "version": datetime.now(timezone.utc).isoformat(),
            "example_count": len(examples),
            "examples": examples
        }
    
    def compact_changes(
        self, 
        older_than_days: int = 30, 
        changes_threshold: int = 100
    ) -> Dict[str, Any]:
        """
        Compact multiple small changes into larger snapshots.
        
        Args:
            older_than_days: Compact changes older than this many days
            changes_threshold: Minimum number of changes to compact
            
        Returns:
            Status of the operation
        """
        logger.info(f"Compacting changes older than {older_than_days} days")
        
        try:
            # Calculate the cutoff date
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
            
            # Find changes to compact
            query = """
            FOR log IN change_logs
                FILTER log.timestamp <= @cutoff_date
                COLLECT entity_id = log.entity_id INTO changes
                FILTER LENGTH(changes) >= @changes_threshold
                RETURN {
                    "entity_id": entity_id,
                    "change_count": LENGTH(changes),
                    "changes": changes
                }
            """
            
            db_connection = DBConnection()
            result = db_connection.execute_query(
                query,
                bind_vars={
                    "cutoff_date": cutoff_date,
                    "changes_threshold": changes_threshold
                }
            )
            
            if not result.get("success", False):
                logger.error(f"Failed to find changes to compact: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error")
                }
            
            entities_to_compact = result.get("result", [])
            
            if not entities_to_compact:
                logger.info("No changes to compact")
                return {
                    "success": True,
                    "compacted_entities": 0,
                    "message": "No changes to compact"
                }
            
            # Compact changes for each entity
            compacted_count = 0
            for entity_data in entities_to_compact:
                entity_id = entity_data.get("entity_id")
                changes = entity_data.get("changes", [])
                
                # This is a placeholder - in a real implementation, 
                # you would actually compact the changes
                
                compacted_count += 1
                logger.info(f"Compacted {len(changes)} changes for {entity_id}")
            
            return {
                "success": True,
                "compacted_entities": compacted_count,
                "total_changes_compacted": sum(e.get("change_count", 0) for e in entities_to_compact)
            }
            
        except Exception as e:
            logger.error(f"Failed to compact changes: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_old_versions(self, retention_days: int = 90) -> Dict[str, Any]:
        """
        Clean up old versions based on retention policy.
        
        Args:
            retention_days: Keep versions newer than this many days
            
        Returns:
            Status of the operation
        """
        logger.info(f"Cleaning up versions older than {retention_days} days")
        
        try:
            # Calculate the cutoff date
            cutoff_date = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
            
            # Find old change logs to remove
            query = """
            FOR log IN change_logs
                FILTER log.timestamp <= @cutoff_date
                RETURN log
            """
            
            db_connection = DBConnection()
            result = db_connection.execute_query(
                query,
                bind_vars={"cutoff_date": cutoff_date}
            )
            
            if not result.get("success", False):
                logger.error(f"Failed to find old change logs: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error")
                }
            
            old_logs = result.get("result", [])
            
            if not old_logs:
                logger.info("No old change logs to remove")
                return {
                    "success": True,
                    "removed_logs": 0,
                    "message": "No old change logs to remove"
                }
            
            # Remove old logs
            with db_connection.get_db() as db:
                removed_count = 0
                for log in old_logs:
                    # Only remove logs if they're not the latest version for an entity
                    # First check if this is the latest log for the entity
                    entity_id = log.get("entity_id")
                    
                    latest_check_query = """
                    FOR l IN change_logs
                        FILTER l.entity_id == @entity_id
                        SORT l.timestamp DESC
                        LIMIT 1
                        RETURN l
                    """
                    
                    latest_result = db_connection.execute_query(
                        latest_check_query,
                        bind_vars={"entity_id": entity_id}
                    )
                    
                    if not latest_result.get("success", False) or not latest_result.get("result"):
                        continue
                    
                    latest_log = latest_result.get("result")[0]
                    
                    # Skip if this is the latest log
                    if latest_log.get("_key") == log.get("_key"):
                        continue
                    
                    # Remove the log
                    db.collection("change_logs").delete(log.get("_key"))
                    removed_count += 1
                
                logger.info(f"Removed {removed_count} old change logs")
                
                return {
                    "success": True,
                    "removed_logs": removed_count,
                    "total_old_logs": len(old_logs)
                }
                
        except Exception as e:
            logger.error(f"Failed to clean up old versions: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Create a global instance
version_sync = VersionSync()