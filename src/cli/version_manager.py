"""
Command Line Interface for HADES Version Management.

This tool provides commands to:
1. Generate training data from knowledge graph diffs
2. Perform housekeeping operations on versioned data
3. Compare different versions of the knowledge graph
"""
import argparse
import json
import sys
from datetime import datetime

from src.db.connection import connection
from src.utils.logger import get_logger
from src.utils.versioning import KGVersion
from src.utils.version_sync import version_sync

logger = get_logger(__name__)


def generate_training_data(args):
    """Generate training data based on knowledge graph diffs."""
    start_version = args.start_version
    end_version = args.end_version
    output_file = args.output
    
    if not start_version or not end_version:
        logger.error("Both start and end versions are required")
        sys.exit(1)
    
    # Generate the training data
    result = version_sync.generate_training_data_from_diff(
        start_version=start_version,
        end_version=end_version,
        output_file=output_file
    )
    
    if not result.get("success", False):
        logger.error(f"Failed to generate training data: {result.get('error')}")
        sys.exit(1)
    
    logger.info(f"Training data generation successful: {json.dumps(result, indent=2)}")


def compact_changes(args):
    """Compact multiple small changes into larger snapshots."""
    older_than_days = args.days
    changes_threshold = args.threshold
    
    # Compact the changes
    result = version_sync.compact_changes(
        older_than_days=older_than_days,
        changes_threshold=changes_threshold
    )
    
    if not result.get("success", False):
        logger.error(f"Failed to compact changes: {result.get('error')}")
        sys.exit(1)
    
    logger.info(f"Change compaction successful: {json.dumps(result, indent=2)}")


def cleanup_versions(args):
    """Clean up old versions based on retention policy."""
    retention_days = args.days
    
    # Clean up old versions
    result = version_sync.cleanup_old_versions(
        retention_days=retention_days
    )
    
    if not result.get("success", False):
        logger.error(f"Failed to clean up old versions: {result.get('error')}")
        sys.exit(1)
    
    logger.info(f"Version cleanup successful: {json.dumps(result, indent=2)}")


def compare_versions(args):
    """Compare two versions of a document."""
    collection = args.collection
    document_id = args.document_id
    version1 = args.version1
    version2 = args.version2
    
    if not all([collection, document_id, version1, version2]):
        logger.error("All parameters (collection, document_id, version1, version2) are required")
        sys.exit(1)
    
    # Compare the versions
    result = connection.compare_versions(
        collection=collection,
        document_id=document_id,
        version1=version1,
        version2=version2
    )
    
    if not result.get("success", False):
        logger.error(f"Failed to compare versions: {result.get('error')}")
        sys.exit(1)
    
    # Pretty print the diff
    print("\nVersion Comparison Result:")
    print(f"Document: {document_id}")
    print(f"Comparing {version1} -> {version2}\n")
    
    diff = result.get("diff", {})
    
    # Print added fields
    if diff.get("added"):
        print("Added Fields:")
        for key, value in diff["added"].items():
            print(f"  + {key}: {value}")
        print()
    
    # Print removed fields
    if diff.get("removed"):
        print("Removed Fields:")
        for key, value in diff["removed"].items():
            print(f"  - {key}: {value}")
        print()
    
    # Print modified fields
    if diff.get("modified"):
        print("Modified Fields:")
        for key, changes in diff["modified"].items():
            print(f"  ~ {key}:")
            print(f"    From: {changes.get('from')}")
            print(f"    To:   {changes.get('to')}")
        print()
    
    if not any([diff.get("added"), diff.get("removed"), diff.get("modified")]):
        print("No differences found between these versions.")


def get_document_history(args):
    """Get the version history of a document."""
    collection = args.collection
    document_id = args.document_id
    
    if not collection or not document_id:
        logger.error("Both collection and document_id are required")
        sys.exit(1)
    
    # Get the document history
    result = connection.get_document_history(
        collection=collection,
        document_id=document_id
    )
    
    if not result.get("success", False):
        logger.error(f"Failed to get document history: {result.get('error')}")
        sys.exit(1)
    
    history = result.get("result", [])
    
    if not history:
        print(f"No version history found for {document_id}")
        return
    
    # Pretty print the history
    print(f"\nVersion History for {document_id}:")
    print(f"Total versions: {len(history)}\n")
    
    for i, entry in enumerate(history):
        print(f"[{i+1}] Version: {entry.get('new_version')}")
        print(f"    Timestamp: {entry.get('timestamp')}")
        print(f"    Commit ID: {entry.get('commit_id')}")
        print(f"    Message: {entry.get('commit_message')}")
        
        # Summarize changes
        changes = entry.get("changes", {})
        added = len(changes.get("added", {}))
        removed = len(changes.get("removed", {}))
        modified = len(changes.get("modified", {}))
        
        if any([added, removed, modified]):
            print(f"    Changes: {added} added, {removed} removed, {modified} modified")
        
        if i < len(history) - 1:
            print()


def main():
    """Main entry point for the version manager CLI."""
    parser = argparse.ArgumentParser(
        description="HADES Knowledge Graph Version Manager"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Generate training data command
    gen_parser = subparsers.add_parser(
        "generate-training",
        help="Generate training data from KG diffs"
    )
    gen_parser.add_argument(
        "--start-version", 
        required=True,
        help="Starting version for the diff"
    )
    gen_parser.add_argument(
        "--end-version", 
        required=True,
        help="Ending version for the diff"
    )
    gen_parser.add_argument(
        "--output", 
        help="Output file name (without path)"
    )
    gen_parser.set_defaults(func=generate_training_data)
    
    # Compact changes command
    compact_parser = subparsers.add_parser(
        "compact", 
        help="Compact multiple small changes into larger snapshots"
    )
    compact_parser.add_argument(
        "--days", 
        type=int, 
        default=30,
        help="Compact changes older than this many days"
    )
    compact_parser.add_argument(
        "--threshold", 
        type=int, 
        default=100,
        help="Minimum number of changes to compact"
    )
    compact_parser.set_defaults(func=compact_changes)
    
    # Cleanup versions command
    cleanup_parser = subparsers.add_parser(
        "cleanup", 
        help="Clean up old versions based on retention policy"
    )
    cleanup_parser.add_argument(
        "--days", 
        type=int, 
        default=90,
        help="Keep versions newer than this many days"
    )
    cleanup_parser.set_defaults(func=cleanup_versions)
    
    # Compare versions command
    compare_parser = subparsers.add_parser(
        "compare", 
        help="Compare two versions of a document"
    )
    compare_parser.add_argument(
        "--collection", 
        required=True,
        help="Collection name"
    )
    compare_parser.add_argument(
        "--document-id", 
        required=True,
        help="Document ID"
    )
    compare_parser.add_argument(
        "--version1", 
        required=True,
        help="First version to compare"
    )
    compare_parser.add_argument(
        "--version2", 
        required=True,
        help="Second version to compare"
    )
    compare_parser.set_defaults(func=compare_versions)
    
    # History command
    history_parser = subparsers.add_parser(
        "history", 
        help="Get the version history of a document"
    )
    history_parser.add_argument(
        "--collection", 
        required=True,
        help="Collection name"
    )
    history_parser.add_argument(
        "--document-id", 
        required=True,
        help="Document ID"
    )
    history_parser.set_defaults(func=get_document_history)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main() 