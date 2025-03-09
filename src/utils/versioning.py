"""
Differential Versioning System for HADES Knowledge Graph.

This module implements a Git-like versioning system for the ArangoDB knowledge graph,
allowing for historical tracking, comparisons between versions, and efficient updates
to downstream processes like GNN training.
"""
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timezone
import uuid
import json

from src.utils.logger import get_logger

logger = get_logger(__name__)


class KGVersion:
    """Knowledge Graph Version model."""
    
    VERSION_PREFIX = "v"
    
    @staticmethod
    def generate_version_id(major: int = 0, minor: int = 0, patch: int = 1) -> str:
        """Generate a semantic version string."""
        return f"{KGVersion.VERSION_PREFIX}{major}.{minor}.{patch}"
    
    @staticmethod
    def increment_version(current_version: str, level: str = "patch") -> str:
        """
        Increment a version number at the specified level.
        
        Args:
            current_version: Current version string (e.g., "v1.2.3")
            level: Which part to increment ("major", "minor", "patch")
            
        Returns:
            New version string
        """
        if not current_version.startswith(KGVersion.VERSION_PREFIX):
            current_version = f"{KGVersion.VERSION_PREFIX}{current_version}"
        
        # Remove prefix for parsing
        version_parts = current_version[len(KGVersion.VERSION_PREFIX):].split(".")
        major, minor, patch = map(int, version_parts)
        
        if level == "major":
            major += 1
            minor = 0
            patch = 0
        elif level == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1
            
        return KGVersion.generate_version_id(major, minor, patch)
    
    @staticmethod 
    def parse_version(version_str: str) -> Tuple[int, int, int]:
        """Parse a version string into its components."""
        if not version_str.startswith(KGVersion.VERSION_PREFIX):
            version_str = f"{KGVersion.VERSION_PREFIX}{version_str}"
        
        # Remove prefix for parsing
        version_parts = version_str[len(KGVersion.VERSION_PREFIX):].split(".")
        return tuple(map(int, version_parts))
    
    @staticmethod
    def compare_versions(v1: str, v2: str) -> int:
        """
        Compare two version strings.
        
        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        v1_parts = KGVersion.parse_version(v1)
        v2_parts = KGVersion.parse_version(v2)
        
        if v1_parts < v2_parts:
            return -1
        elif v1_parts > v2_parts:
            return 1
        else:
            return 0


class VersionMetadata:
    """Metadata fields to be added to versioned documents."""
    
    @staticmethod
    def create_metadata(version: str, commit_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create version metadata for a new document.
        
        Args:
            version: Version string
            commit_id: Optional commit ID (generated if not provided)
            
        Returns:
            Dictionary with version metadata
        """
        now = datetime.now(timezone.utc).isoformat()
        return {
            "version": version,
            "created_at": now,
            "updated_at": now,
            "valid_from": now,
            "valid_until": None,  # null means currently valid
            "commit_id": commit_id or str(uuid.uuid4()),
            "previous_version": None,
        }
    
    @staticmethod
    def update_metadata(
        existing_metadata: Dict[str, Any], 
        new_version: str,
        commit_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update version metadata for an existing document.
        
        Args:
            existing_metadata: Previous version metadata
            new_version: New version string
            commit_id: Optional commit ID (generated if not provided)
            
        Returns:
            Updated metadata dictionary
        """
        now = datetime.now(timezone.utc).isoformat()
        return {
            "version": new_version,
            "created_at": existing_metadata.get("created_at"),  # preserve original creation date
            "updated_at": now,
            "valid_from": now,
            "valid_until": None,  # null means currently valid
            "commit_id": commit_id or str(uuid.uuid4()),
            "previous_version": existing_metadata.get("version"),
        }
    
    @staticmethod
    def expire_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mark a document as expired (no longer valid).
        
        Args:
            metadata: Current metadata
            
        Returns:
            Updated metadata with expiration timestamp
        """
        updated = metadata.copy()
        updated["valid_until"] = datetime.now(timezone.utc).isoformat()
        return updated


class ChangeLog:
    """Change log entry for tracking modifications to the knowledge graph."""
    
    @staticmethod
    def create_entry(
        entity_id: str,
        previous_version: Optional[str],
        new_version: str,
        changes: Dict[str, Any],
        commit_id: str,
        commit_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a change log entry.
        
        Args:
            entity_id: ID of the entity that changed
            previous_version: Previous version (None for new entities)
            new_version: New version
            changes: Dictionary containing the changes
            commit_id: Commit ID
            commit_message: Optional commit message
            
        Returns:
            Change log entry as a dictionary
        """
        return {
            "_key": str(uuid.uuid4()),  # Generate a unique ID for the change log
            "entity_id": entity_id,
            "previous_version": previous_version,
            "new_version": new_version,
            "commit_id": commit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "changes": changes,
            "commit_message": commit_message or f"Updated {entity_id} to {new_version}",
        }
    
    @staticmethod
    def compute_diff(old_doc: Dict[str, Any], new_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute the difference between two document versions.
        
        Args:
            old_doc: Previous version of the document
            new_doc: New version of the document
            
        Returns:
            Dictionary with added, removed, and modified fields
        """
        # Make copies to avoid modifying the originals
        old = old_doc.copy() if old_doc else {}
        new = new_doc.copy() if new_doc else {}
        
        # Remove metadata fields from the comparison
        for doc in (old, new):
            for meta_field in ("version", "created_at", "updated_at", "valid_from", 
                              "valid_until", "commit_id", "previous_version"):
                doc.pop(meta_field, None)
        
        # Compute differences
        added = {}
        removed = {}
        modified = {}
        
        # Find added and modified fields
        for key, new_value in new.items():
            if key not in old:
                added[key] = new_value
            elif old[key] != new_value:
                modified[key] = {
                    "from": old[key],
                    "to": new_value
                }
        
        # Find removed fields
        for key in old:
            if key not in new:
                removed[key] = old[key]
        
        return {
            "added": added,
            "removed": removed,
            "modified": modified
        }


# Create a global instance for versioning operations
versioning = KGVersion() 