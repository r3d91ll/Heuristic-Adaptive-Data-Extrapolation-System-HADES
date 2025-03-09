import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import hashlib
import concurrent.futures
from pydantic import BaseModel, ValidationError, Field, validator
from ..db.connection import get_db_connection
from ..utils.versioning import KGVersion, VersionMetadata

# Pydantic models for data validation
class EntityBase(BaseModel):
    """Base model for entity data validation."""
    name: str
    type: str
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("name")
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v
    
    @validator("type")
    def type_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Type cannot be empty")
        return v


class RelationshipBase(BaseModel):
    """Base model for relationship data validation."""
    _from: str
    _to: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("_from", "_to")
    def entity_refs_valid(cls, v):
        if not v.startswith("entities/"):
            raise ValueError("Entity references must start with 'entities/'")
        return v
    
    @validator("type")
    def type_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Type cannot be empty")
        return v


class DataIngestionManager:
    """
    Manager for data ingestion processes with validation, preprocessing, and error handling.
    """
    
    def __init__(self, db_connection=None):
        self.logger = logging.getLogger(__name__)
        self.db = db_connection or get_db_connection()
        self.version_metadata = VersionMetadata(self.db)
    
    def ingest(self, 
              data: Union[Dict[str, Any], List[Dict[str, Any]]], 
              data_type: str = "entity",
              validation_level: str = "strict",
              update_version: bool = True,
              batch_size: int = 100) -> Dict[str, Any]:
        """
        Ingest data into the knowledge graph with validation and preprocessing.
        
        Args:
            data: Entity or relationship data to ingest
            data_type: Type of data to ingest (entity or relationship)
            validation_level: Validation level (strict, medium, or lenient)
            update_version: Whether to update version metadata
            batch_size: Size of batches for batch processing
            
        Returns:
            Ingestion results
        """
        self.logger.info(f"Ingesting {data_type} data with validation level: {validation_level}")
        
        # Convert single item to list for uniform processing
        data_list = data if isinstance(data, list) else [data]
        
        if not data_list:
            return {
                "status": "error",
                "message": "No data provided",
                "inserted": 0,
                "errors": []
            }
        
        # Validate and preprocess data
        validation_results = self._validate_and_preprocess(data_list, data_type, validation_level)
        valid_data = validation_results["valid_data"]
        errors = validation_results["errors"]
        
        # If strict validation and there are errors, abort
        if validation_level == "strict" and errors:
            return {
                "status": "error",
                "message": "Validation errors found in strict mode",
                "inserted": 0,
                "errors": errors
            }
        
        # Process data in batches if needed
        if len(valid_data) > batch_size:
            return self._batch_process(valid_data, data_type, update_version, batch_size, errors)
        
        # Process data directly
        result = self._process_data(valid_data, data_type, update_version)
        
        # Merge errors from validation and processing
        all_errors = errors + result.get("errors", [])
        
        return {
            "status": "success" if not all_errors else "partial",
            "message": f"Ingested {result.get('inserted', 0)} items with {len(all_errors)} errors",
            "inserted": result.get("inserted", 0),
            "errors": all_errors
        }
    
    def _validate_and_preprocess(self, 
                               data_list: List[Dict[str, Any]], 
                               data_type: str,
                               validation_level: str) -> Dict[str, Any]:
        """
        Validate and preprocess data before ingestion.
        
        Args:
            data_list: List of data items to validate
            data_type: Type of data (entity or relationship)
            validation_level: Validation level (strict, medium, or lenient)
            
        Returns:
            Dictionary with valid data and errors
        """
        self.logger.info(f"Validating {len(data_list)} {data_type} items")
        
        valid_data = []
        errors = []
        
        for idx, item in enumerate(data_list):
            try:
                # Validate using Pydantic models
                if data_type == "entity":
                    validated_item = EntityBase(**item).dict()
                    
                    # Add _key if not present (for ArangoDB)
                    if "_key" not in validated_item:
                        validated_item["_key"] = self._generate_key(validated_item["name"], validated_item["type"])
                    
                    # Enrich with preprocessed fields
                    validated_item["created_at"] = validated_item.get("created_at", datetime.now().isoformat())
                    validated_item["updated_at"] = datetime.now().isoformat()
                    
                elif data_type == "relationship":
                    validated_item = RelationshipBase(**item).dict()
                    
                    # Add _key if not present (for ArangoDB)
                    if "_key" not in validated_item:
                        validated_item["_key"] = self._generate_key(validated_item["_from"], validated_item["_to"], validated_item["type"])
                    
                    # Enrich with preprocessed fields
                    validated_item["created_at"] = validated_item.get("created_at", datetime.now().isoformat())
                    validated_item["updated_at"] = datetime.now().isoformat()
                
                else:
                    errors.append({
                        "index": idx,
                        "item": item,
                        "error": f"Unknown data type: {data_type}"
                    })
                    continue
                
                # Additional custom validation and enrichment
                if data_type == "entity":
                    # Check for required properties based on entity type
                    if validated_item["type"] == "person" and "birth_date" not in validated_item["properties"]:
                        if validation_level == "strict":
                            errors.append({
                                "index": idx,
                                "item": item,
                                "error": "Person entity missing birth_date property"
                            })
                            continue
                        elif validation_level == "medium":
                            self.logger.warning(f"Person entity missing birth_date property: {validated_item['name']}")
                    
                    # Normalize certain properties
                    if "aliases" in validated_item["properties"] and isinstance(validated_item["properties"]["aliases"], str):
                        validated_item["properties"]["aliases"] = [alias.strip() for alias in validated_item["properties"]["aliases"].split(",")]
                
                valid_data.append(validated_item)
                
            except ValidationError as e:
                # Handle validation errors
                if validation_level in ["strict", "medium"]:
                    errors.append({
                        "index": idx,
                        "item": item,
                        "error": str(e)
                    })
                else:
                    # For lenient validation, log but accept with default values where possible
                    self.logger.warning(f"Validation error (lenient mode): {e}")
                    try:
                        # Attempt to create a minimal valid item
                        if data_type == "entity":
                            validated_item = {
                                "name": item.get("name", f"Unknown-{idx}"),
                                "type": item.get("type", "unknown"),
                                "properties": item.get("properties", {}),
                                "_key": self._generate_key(item.get("name", f"Unknown-{idx}"), item.get("type", "unknown")),
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                            valid_data.append(validated_item)
                        elif data_type == "relationship" and "_from" in item and "_to" in item:
                            validated_item = {
                                "_from": item["_from"],
                                "_to": item["_to"],
                                "type": item.get("type", "unknown"),
                                "properties": item.get("properties", {}),
                                "_key": self._generate_key(item["_from"], item["_to"], item.get("type", "unknown")),
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                            valid_data.append(validated_item)
                        else:
                            errors.append({
                                "index": idx,
                                "item": item,
                                "error": str(e)
                            })
                    except Exception as ex:
                        errors.append({
                            "index": idx,
                            "item": item,
                            "error": f"Failed to create minimal valid item: {ex}"
                        })
            
            except Exception as e:
                # Handle other errors
                errors.append({
                    "index": idx,
                    "item": item,
                    "error": f"Unexpected error: {str(e)}"
                })
        
        self.logger.info(f"Validation complete: {len(valid_data)} valid, {len(errors)} errors")
        return {
            "valid_data": valid_data,
            "errors": errors
        }
    
    def _process_data(self, 
                     data_list: List[Dict[str, Any]], 
                     data_type: str,
                     update_version: bool) -> Dict[str, Any]:
        """
        Process validated data for insertion into the database.
        
        Args:
            data_list: List of validated data items
            data_type: Type of data (entity or relationship)
            update_version: Whether to update version metadata
            
        Returns:
            Processing results
        """
        self.logger.info(f"Processing {len(data_list)} {data_type} items")
        
        inserted = 0
        errors = []
        
        collection = "entities" if data_type == "entity" else "relationships"
        
        for idx, item in enumerate(data_list):
            try:
                # Add version information if requested
                if update_version:
                    version = KGVersion.new_patch()  # Increment patch version
                    item["version"] = version.to_string()
                
                # Check if item already exists
                query = f"""
                FOR doc IN {collection}
                    FILTER doc._key == @key
                    RETURN doc
                """
                cursor = self.db.aql.execute(query, bind_vars={"key": item["_key"]})
                existing = [doc for doc in cursor]
                
                if existing:
                    # Update existing document
                    update_query = f"""
                    UPDATE @key WITH @item IN {collection}
                    RETURN NEW
                    """
                    self.db.aql.execute(update_query, bind_vars={"key": item["_key"], "item": item})
                    
                    # Log change if version tracking enabled
                    if update_version:
                        self.version_metadata.log_change(
                            collection=collection,
                            document_id=f"{collection}/{item['_key']}",
                            change_type="updated",
                            old_value=existing[0],
                            new_value=item,
                            version=version
                        )
                else:
                    # Insert new document
                    insert_query = f"""
                    INSERT @item INTO {collection}
                    RETURN NEW
                    """
                    self.db.aql.execute(insert_query, bind_vars={"item": item})
                    
                    # Log change if version tracking enabled
                    if update_version:
                        self.version_metadata.log_change(
                            collection=collection,
                            document_id=f"{collection}/{item['_key']}",
                            change_type="added",
                            old_value=None,
                            new_value=item,
                            version=version
                        )
                
                inserted += 1
                
            except Exception as e:
                # Handle database errors
                errors.append({
                    "index": idx,
                    "item": item,
                    "error": f"Database error: {str(e)}"
                })
        
        self.logger.info(f"Processing complete: {inserted} inserted, {len(errors)} errors")
        return {
            "inserted": inserted,
            "errors": errors
        }
    
    def _batch_process(self, 
                      data_list: List[Dict[str, Any]], 
                      data_type: str,
                      update_version: bool,
                      batch_size: int,
                      existing_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process data in batches for better performance.
        
        Args:
            data_list: List of validated data items
            data_type: Type of data (entity or relationship)
            update_version: Whether to update version metadata
            batch_size: Size of batches
            existing_errors: Errors from validation
            
        Returns:
            Processing results
        """
        self.logger.info(f"Batch processing {len(data_list)} {data_type} items with batch size {batch_size}")
        
        # Split data into batches
        batches = [data_list[i:i + batch_size] for i in range(0, len(data_list), batch_size)]
        
        total_inserted = 0
        total_errors = existing_errors.copy()
        
        for batch_idx, batch in enumerate(batches):
            self.logger.info(f"Processing batch {batch_idx + 1}/{len(batches)}")
            
            result = self._process_data(batch, data_type, update_version)
            
            total_inserted += result.get("inserted", 0)
            total_errors.extend(result.get("errors", []))
        
        self.logger.info(f"Batch processing complete: {total_inserted} inserted, {len(total_errors)} errors")
        return {
            "status": "success" if not total_errors else "partial",
            "message": f"Ingested {total_inserted} items with {len(total_errors)} errors",
            "inserted": total_inserted,
            "errors": total_errors
        }
    
    def _generate_key(self, *args) -> str:
        """
        Generate a unique key for the database.
        
        Args:
            *args: Values to use for key generation
            
        Returns:
            Generated key
        """
        # Create a deterministic key based on input values
        key_string = "_".join(str(arg) for arg in args)
        
        # Use a hash to ensure uniqueness and manageable length
        hash_object = hashlib.md5(key_string.encode())
        return hash_object.hexdigest() 