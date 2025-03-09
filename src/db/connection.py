"""
ArangoDB connection management for HADES.
"""
import os
from contextlib import contextmanager
from typing import Dict, Generator, Optional, Union, Any
import uuid

from arango import ArangoClient
from arango.database import Database
from arango.exceptions import ArangoError

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ArangoDBConnection:
    """Manages connections to ArangoDB."""

    def __init__(
        self,
        host: str = os.getenv("ARANGO_HOST", "http://localhost:8529"),
        username: str = os.getenv("ARANGO_USERNAME", "root"),
        password: str = os.getenv("ARANGO_PASSWORD", ""),
        database: str = os.getenv("ARANGO_DATABASE", "hades"),
    ):
        """Initialize the ArangoDB connection."""
        self.host = host
        self.username = username
        self.password = password
        self.database_name = database
        self.client = ArangoClient(hosts=host)

    def initialize_database(self) -> None:
        """Initialize the database and collections if they don't exist."""
        sys_db = self.client.db("_system", username=self.username, password=self.password)

        # Create database if it doesn't exist
        if not sys_db.has_database(self.database_name):
            logger.info(f"Creating database: {self.database_name}")
            sys_db.create_database(
                self.database_name,
                users=[{"username": self.username, "password": self.password, "active": True}],
            )

        # Connect to the database
        db = self.client.db(
            self.database_name, username=self.username, password=self.password
        )

        # Create document collections
        document_collections = ["entities", "contexts", "domains", "change_logs", "verifications"]
        for collection in document_collections:
            if not db.has_collection(collection):
                logger.info(f"Creating document collection: {collection}")
                db.create_collection(collection)

        # Create edge collections
        edge_collections = ["relationships", "entity_domains", "entity_contexts"]
        for collection in edge_collections:
            if not db.has_collection(collection):
                logger.info(f"Creating edge collection: {collection}")
                db.create_collection(collection, edge=True)

        # Create indexes
        logger.info("Ensuring indexes")
        db.collection("entities").add_persistent_index(["name", "type"])
        db.collection("relationships").add_persistent_index(["_from", "_to", "type"])
        db.collection("contexts").add_fulltext_index(["text"])
        
        # Version-related indexes
        db.collection("entities").add_persistent_index(["version"])
        db.collection("entities").add_persistent_index(["valid_from", "valid_until"])
        db.collection("entities").add_persistent_index(["commit_id"])
        
        db.collection("relationships").add_persistent_index(["version"])
        db.collection("relationships").add_persistent_index(["valid_from", "valid_until"])
        db.collection("relationships").add_persistent_index(["commit_id"])
        
        # Change log indexes
        db.collection("change_logs").add_persistent_index(["entity_id"])
        db.collection("change_logs").add_persistent_index(["commit_id"])
        db.collection("change_logs").add_persistent_index(["timestamp"])
        db.collection("change_logs").add_persistent_index(["previous_version", "new_version"])
        
        # Verification indexes
        db.collection("verifications").add_persistent_index(["text_id"])
        db.collection("verifications").add_persistent_index(["version"])
        db.collection("verifications").add_persistent_index(["timestamp"])
        db.collection("verifications").add_persistent_index(["verification_rate"])

    @contextmanager
    def get_db(self) -> Generator[Database, None, None]:
        """Get a database connection."""
        db = self.client.db(
            self.database_name, username=self.username, password=self.password
        )
        try:
            yield db
        except ArangoError as e:
            logger.error(f"ArangoDB error: {e}")
            raise
        finally:
            # No need to close connection as ArangoDB client manages the connection pool
            pass

    def execute_query(
        self, 
        query: str, 
        bind_vars: Optional[Dict] = None,
        as_of_version: Optional[str] = None,
        as_of_timestamp: Optional[str] = None
    ) -> Dict:
        """
        Execute an AQL query, optionally with version constraints.
        
        Args:
            query: The AQL query string
            bind_vars: Optional query parameters
            as_of_version: Optional version filter for time-travel queries
            as_of_timestamp: Optional timestamp for time-travel queries
            
        Returns:
            Query results
        """
        with self.get_db() as db:
            try:
                vars_dict = bind_vars or {}
                
                # Add version constraints if provided
                if as_of_version or as_of_timestamp:
                    # If both are provided, timestamp takes precedence
                    if as_of_timestamp:
                        vars_dict["_as_of_timestamp"] = as_of_timestamp
                        # Modify the query to add version constraints based on timestamp
                        query = self._add_timestamp_filter(query)
                    else:
                        vars_dict["_as_of_version"] = as_of_version
                        # Modify the query to add version constraints based on version
                        query = self._add_version_filter(query)
                
                result = db.aql.execute(query, bind_vars=vars_dict)
                return {"success": True, "result": list(result)}
            except ArangoError as e:
                logger.error(f"Query execution error: {e}")
                return {"success": False, "error": str(e)}
    
    def _add_timestamp_filter(self, query: str) -> str:
        """
        Add timestamp-based filtering to a query for time-travel.
        
        Args:
            query: Original AQL query
            
        Returns:
            Modified query with timestamp filtering
        """
        # A very simple implementation - in production you would use a proper AQL parser
        # This assumes collection names are directly after FOR statements
        for collection in ["entities", "relationships"]:
            # Add timestamp filtering to each mention of these collections
            query = query.replace(
                f"FOR {collection[0]} IN {collection}",
                f"""FOR {collection[0]} IN {collection}
                    FILTER 
                        {collection[0]}.valid_from <= @_as_of_timestamp AND
                        ({collection[0]}.valid_until >= @_as_of_timestamp OR {collection[0]}.valid_until == null)"""
            )
        return query
    
    def _add_version_filter(self, query: str) -> str:
        """
        Add version-based filtering to a query for time-travel.
        
        Args:
            query: Original AQL query
            
        Returns:
            Modified query with version filtering
        """
        # A very simple implementation - in production you would use a proper AQL parser
        # This assumes collection names are directly after FOR statements
        for collection in ["entities", "relationships"]:
            # Add version filtering to each mention of these collections
            query = query.replace(
                f"FOR {collection[0]} IN {collection}",
                f"""FOR {collection[0]} IN {collection}
                    FILTER {collection[0]}.version == @_as_of_version"""
            )
        return query
    
    def insert_document(
        self, 
        collection: str, 
        document: Dict[str, Any],
        versioned: bool = True
    ) -> Dict[str, Any]:
        """
        Insert a document with versioning support.
        
        Args:
            collection: Collection name
            document: Document to insert
            versioned: Whether to add version metadata
            
        Returns:
            Insert operation result
        """
        try:
            with self.get_db() as db:
                # If versioning is enabled and metadata not already present,
                # add version metadata
                if versioned and "version" not in document:
                    from src.utils.versioning import VersionMetadata
                    version_meta = VersionMetadata.create_metadata("v0.1.0")
                    document.update(version_meta)
                
                result = db.collection(collection).insert(document)
                
                # Log the change if versioned
                if versioned:
                    self._log_change(
                        entity_id=result["_id"],
                        previous_version=None,
                        new_version=document["version"],
                        changes={"added": document},
                        commit_id=document["commit_id"]
                    )
                
                return {"success": True, "result": result}
        except ArangoError as e:
            logger.error(f"Insert error: {e}")
            return {"success": False, "error": str(e)}
    
    def update_document(
        self, 
        collection: str, 
        document_key: str, 
        update_data: Dict[str, Any],
        versioned: bool = True
    ) -> Dict[str, Any]:
        """
        Update a document with versioning support.
        
        Args:
            collection: Collection name
            document_key: Document key to update
            update_data: New data for the document
            versioned: Whether to use versioning
            
        Returns:
            Update operation result
        """
        try:
            with self.get_db() as db:
                col = db.collection(collection)
                
                # Get the current document
                current_doc = col.get(document_key)
                if not current_doc:
                    return {"success": False, "error": f"Document {document_key} not found"}
                
                if versioned:
                    # Import here to avoid circular imports
                    from src.utils.versioning import VersionMetadata, KGVersion, ChangeLog
                    
                    # Create a new version of the document
                    current_metadata = {
                        k: current_doc.get(k) for k in 
                        ["version", "created_at", "updated_at", "valid_from", 
                         "valid_until", "commit_id", "previous_version"]
                    }
                    
                    # Generate new version and commit ID
                    new_version = KGVersion.increment_version(current_doc.get("version", "v0.0.0"))
                    commit_id = str(uuid.uuid4())
                    
                    # Expire the current document
                    col.update(
                        document_key, 
                        VersionMetadata.expire_metadata(current_metadata)
                    )
                    
                    # Create a new document with updated data and new version metadata
                    new_doc = current_doc.copy()
                    new_doc.update(update_data)
                    
                    # Remove key so it creates a new document
                    new_key = f"{document_key}:{new_version}"
                    if "_key" in new_doc:
                        del new_doc["_key"]
                    
                    # Set new _key and version metadata
                    new_doc["_key"] = new_key
                    new_doc.update(
                        VersionMetadata.update_metadata(
                            current_metadata, 
                            new_version,
                            commit_id
                        )
                    )
                    
                    # Insert the new version
                    result = col.insert(new_doc)
                    
                    # Log the change
                    self._log_change(
                        entity_id=current_doc["_id"],
                        previous_version=current_doc.get("version"),
                        new_version=new_version,
                        changes=ChangeLog.compute_diff(current_doc, new_doc),
                        commit_id=commit_id
                    )
                    
                    return {"success": True, "result": result}
                else:
                    # Standard update without versioning
                    result = col.update(document_key, update_data)
                    return {"success": True, "result": result}
        except ArangoError as e:
            logger.error(f"Update error: {e}")
            return {"success": False, "error": str(e)}
    
    def _log_change(
        self, 
        entity_id: str, 
        previous_version: Optional[str],
        new_version: str,
        changes: Dict[str, Any],
        commit_id: str,
        commit_message: Optional[str] = None
    ) -> None:
        """Log a change to the change_logs collection."""
        try:
            with self.get_db() as db:
                from src.utils.versioning import ChangeLog
                
                # Create change log entry
                log_entry = ChangeLog.create_entry(
                    entity_id=entity_id,
                    previous_version=previous_version,
                    new_version=new_version,
                    changes=changes,
                    commit_id=commit_id,
                    commit_message=commit_message
                )
                
                # Insert into change_logs collection
                db.collection("change_logs").insert(log_entry)
        except Exception as e:
            logger.error(f"Failed to log change: {e}")
    
    def get_document_history(
        self, 
        collection: str, 
        document_id: str
    ) -> Dict[str, Any]:
        """
        Get the version history of a document.
        
        Args:
            collection: Collection name
            document_id: Document ID
            
        Returns:
            List of change logs for the document
        """
        query = """
        FOR log IN change_logs
            FILTER log.entity_id == @document_id
            SORT log.timestamp DESC
            RETURN log
        """
        
        return self.execute_query(
            query,
            bind_vars={"document_id": document_id}
        )
    
    def get_document_as_of_version(
        self, 
        collection: str, 
        document_id: str, 
        version: str
    ) -> Dict[str, Any]:
        """
        Get a document as it existed at a specific version.
        
        Args:
            collection: Collection name
            document_id: Document ID or key
            version: Version string
            
        Returns:
            Document at the specified version
        """
        query = """
        FOR doc IN @@collection
            FILTER 
                doc._id == @document_id AND 
                doc.version == @version
            RETURN doc
        """
        
        return self.execute_query(
            query,
            bind_vars={
                "@collection": collection,
                "document_id": document_id,
                "version": version
            }
        )
    
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
            Difference between the versions
        """
        from src.utils.versioning import ChangeLog
        
        # Get documents at both versions
        v1_result = self.get_document_as_of_version(collection, document_id, version1)
        v2_result = self.get_document_as_of_version(collection, document_id, version2)
        
        if not v1_result.get("success") or not v2_result.get("success"):
            return {
                "success": False, 
                "error": "Failed to retrieve one or both versions"
            }
        
        v1_docs = v1_result.get("result", [])
        v2_docs = v2_result.get("result", [])
        
        if not v1_docs or not v2_docs:
            return {
                "success": False,
                "error": "One or both versions not found"
            }
        
        # Compute the difference
        diff = ChangeLog.compute_diff(v1_docs[0], v2_docs[0])
        
        return {
            "success": True,
            "document_id": document_id,
            "version1": version1,
            "version2": version2,
            "diff": diff
        }


# Global connection instance
connection = ArangoDBConnection()
