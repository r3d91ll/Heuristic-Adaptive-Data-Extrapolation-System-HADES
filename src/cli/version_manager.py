from typing import Any, Dict, List, Optional
import logging
from src.db.connection import DBConnection

logger = logging.getLogger(__name__)

class VersionManager:
    """
    Version management module for HADES.
    
    This module handles versioning of the knowledge graph and related components.
    """

    def __init__(self):
        """Initialize the VersionManager module."""
        logger.info("Initializing VersionManager module")
        self.db_connection = DBConnection()
    
    def get_versions(self) -> Dict[str, Any]:
        """
        Retrieve all versions of the knowledge graph.
        
        Returns:
            List of version information
        """
        logger.info("Retrieving all versions")
        
        try:
            aql_query = f"""
            FOR doc IN versions
                RETURN {{
                    "version": doc.version,
                    "timestamp": doc.timestamp
                }}
            """
            
            result = self.db_connection.execute_query(aql_query)
            
            if not result["success"]:
                logger.error(f"Version retrieval failed: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error")
                }
            
            versions = result["result"]
            logger.info(f"Retrieved {len(versions)} versions")
            return {
                "success": True,
                "versions": versions
            }
        
        except Exception as e:
            logger.exception("An error occurred while retrieving versions")
            return {
                "success": False,
                "error": str(e)
            }

    def get_version_details(
        self,
        version: str
    ) -> Dict[str, Any]:
        """
        Retrieve details for a specific version of the knowledge graph.
        
        Args:
            version: The version to retrieve details for
            
        Returns:
            Version details and metadata
        """
        logger.info(f"Retrieving details for version: {version}")
        
        try:
            aql_query = f"""
            FOR doc IN versions
                FILTER doc.version == @version
                RETURN {{
                    "version": doc.version,
                    "timestamp": doc.timestamp,
                    "changes": doc.changes
                }}
            """
            
            bind_vars = {
                "version": version
            }
            
            result = self.db_connection.execute_query(aql_query, bind_vars=bind_vars)
            
            if not result["success"]:
                logger.error(f"Version details retrieval failed: {result.get('error')}")
                return {
                    "success": False,
                    "error": result.get("error")
                }
            
            version_details = result["result"][0] if result["result"] else None
            logger.info(f"Retrieved details for version: {version}")
            return {
                "success": True,
                "details": version_details
            }
        
        except Exception as e:
            logger.exception("An error occurred while retrieving version details")
            return {
                "success": False,
                "error": str(e)
            }