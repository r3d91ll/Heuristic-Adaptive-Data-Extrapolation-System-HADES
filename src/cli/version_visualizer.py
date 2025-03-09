"""
Command Line Interface for visualizing HADES version history.

This tool provides visualizations of:
1. Document version history
2. Changes between versions
3. Knowledge graph evolution over time
"""
import argparse
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from src.db.connection import connection
from src.utils.logger import get_logger
from src.utils.versioning import KGVersion

logger = get_logger(__name__)

try:
    # Import visualization libraries if available
    import matplotlib.pyplot as plt
    import networkx as nx
    from matplotlib.lines import Line2D
    HAS_VISUALIZATION = True
except ImportError:
    logger.warning("Matplotlib or NetworkX not installed. Visualization features disabled.")
    logger.warning("Install with: pip install matplotlib networkx")
    HAS_VISUALIZATION = False


def visualize_version_history(args):
    """
    Visualize the version history of a document as a timeline.
    
    Args:
        args: Command line arguments
    """
    if not HAS_VISUALIZATION:
        logger.error("Visualization requires matplotlib and networkx")
        sys.exit(1)
    
    collection = args.collection
    document_id = args.document_id
    output_file = args.output
    
    # Get document history
    history_result = connection.get_document_history(
        collection=collection,
        document_id=document_id
    )
    
    if not history_result.get("success", False):
        logger.error(f"Failed to get document history: {history_result.get('error')}")
        sys.exit(1)
    
    history = history_result.get("result", [])
    
    if not history:
        logger.error(f"No version history found for {document_id}")
        sys.exit(1)
    
    # Create a timeline visualization
    create_timeline_visualization(history, document_id, output_file)
    
    logger.info(f"Timeline visualization created: {output_file}")


def create_timeline_visualization(
    history: List[Dict[str, Any]], 
    document_id: str, 
    output_file: str
):
    """
    Create a timeline visualization of document version history.
    
    Args:
        history: List of change log entries
        document_id: Document ID
        output_file: Output file path
    """
    # Sort history by timestamp
    history.sort(key=lambda x: x.get("timestamp", ""))
    
    # Create figure
    plt.figure(figsize=(12, 8))
    
    # Extract timestamps and versions
    timestamps = [entry.get("timestamp", "") for entry in history]
    versions = [entry.get("new_version", "") for entry in history]
    
    # Convert timestamps to datetime objects
    dates = [datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.now() for ts in timestamps]
    
    # Create y-positions for the timeline
    y_pos = [0] * len(dates)
    
    # Plot the timeline
    plt.plot(dates, y_pos, "-o", color="blue", markersize=10)
    
    # Add version labels
    for i, (date, version) in enumerate(zip(dates, versions)):
        change_count = 0
        added = len(history[i].get("changes", {}).get("added", {}))
        removed = len(history[i].get("changes", {}).get("removed", {}))
        modified = len(history[i].get("changes", {}).get("modified", {}))
        change_count = added + removed + modified
        
        label = f"{version}\n({change_count} changes)"
        plt.annotate(
            label,
            xy=(date, 0),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            va="bottom",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8),
            fontsize=9
        )
    
    # Add the document ID as title
    plt.title(f"Version History: {document_id}")
    
    # Format the x-axis to show dates
    plt.gcf().autofmt_xdate()
    
    # Remove y-axis ticks and labels
    plt.yticks([])
    
    # Save the visualization
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()


def visualize_version_diff(args):
    """
    Visualize the difference between two versions of a document.
    
    Args:
        args: Command line arguments
    """
    if not HAS_VISUALIZATION:
        logger.error("Visualization requires matplotlib and networkx")
        sys.exit(1)
    
    collection = args.collection
    document_id = args.document_id
    version1 = args.version1
    version2 = args.version2
    output_file = args.output
    
    # Compare versions
    compare_result = connection.compare_versions(
        collection=collection,
        document_id=document_id,
        version1=version1,
        version2=version2
    )
    
    if not compare_result.get("success", False):
        logger.error(f"Failed to compare versions: {compare_result.get('error')}")
        sys.exit(1)
    
    # Create diff visualization
    create_diff_visualization(compare_result, document_id, version1, version2, output_file)
    
    logger.info(f"Diff visualization created: {output_file}")


def create_diff_visualization(
    diff_result: Dict[str, Any],
    document_id: str,
    version1: str,
    version2: str,
    output_file: str
):
    """
    Create a visualization of differences between two versions.
    
    Args:
        diff_result: Comparison result
        document_id: Document ID
        version1: First version
        version2: Second version
        output_file: Output file path
    """
    diff = diff_result.get("diff", {})
    
    # Create figure
    plt.figure(figsize=(12, 10))
    
    # Create data for visualization
    added = list(diff.get("added", {}).keys())
    removed = list(diff.get("removed", {}).keys())
    modified = list(diff.get("modified", {}).keys())
    
    # Create a simple bar chart showing the number of changes
    categories = ["Added", "Removed", "Modified"]
    values = [len(added), len(removed), len(modified)]
    colors = ["green", "red", "orange"]
    
    plt.bar(categories, values, color=colors)
    
    # Add value labels on top of bars
    for i, v in enumerate(values):
        plt.text(i, v + 0.1, str(v), ha="center")
    
    # Add title and labels
    plt.title(f"Differences: {document_id}\n{version1} → {version2}")
    plt.ylabel("Number of Fields")
    
    # Create a table with the changes
    if added or removed or modified:
        ax_table = plt.axes([0.1, 0.0, 0.8, 0.4])
        ax_table.axis("off")
        
        table_data = []
        table_colors = []
        
        # Add added fields
        for field in added:
            value = diff["added"][field]
            table_data.append(["Added", field, "", str(value)])
            table_colors.append(["white", "white", "white", "lightgreen"])
        
        # Add removed fields
        for field in removed:
            value = diff["removed"][field]
            table_data.append(["Removed", field, str(value), ""])
            table_colors.append(["white", "white", "lightcoral", "white"])
        
        # Add modified fields
        for field in modified:
            from_val = diff["modified"][field]["from"]
            to_val = diff["modified"][field]["to"]
            table_data.append(["Modified", field, str(from_val), str(to_val)])
            table_colors.append(["white", "white", "lightyellow", "lightyellow"])
        
        # Create table
        if table_data:
            table = plt.table(
                cellText=table_data,
                colLabels=["Type", "Field", version1, version2],
                loc="center",
                cellColours=table_colors
            )
            
            # Set table properties
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 1.5)
    
    # Save the visualization
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()


def visualize_kg_evolution(args):
    """
    Visualize the evolution of a knowledge graph neighborhood over versions.
    
    Args:
        args: Command line arguments
    """
    if not HAS_VISUALIZATION:
        logger.error("Visualization requires matplotlib and networkx")
        sys.exit(1)
    
    entity_id = args.entity_id
    versions = args.versions.split(",") if args.versions else []
    hops = args.hops
    output_file = args.output
    
    if not versions:
        logger.error("At least one version must be specified")
        sys.exit(1)
    
    # Get the entity subgraphs for each version
    subgraphs = []
    for version in versions:
        subgraph = get_entity_subgraph(entity_id, version, hops)
        if subgraph:
            subgraphs.append((version, subgraph))
    
    if not subgraphs:
        logger.error(f"Failed to get subgraphs for entity {entity_id}")
        sys.exit(1)
    
    # Create KG evolution visualization
    create_kg_evolution_visualization(subgraphs, entity_id, output_file)
    
    logger.info(f"Knowledge graph evolution visualization created: {output_file}")


def get_entity_subgraph(
    entity_id: str, 
    version: str, 
    hops: int = 1
) -> Optional[Dict[str, Any]]:
    """
    Get a subgraph centered on an entity for a specific version.
    
    Args:
        entity_id: Entity ID
        version: Version to query
        hops: Number of hops to include
        
    Returns:
        Subgraph data or None if not found
    """
    # Query to get the entity and its neighborhood
    aql_query = """
    LET entity = DOCUMENT(@entity_id)
    
    LET neighborhood = (
        FOR v, e, p IN 1..@hops ANY entity relationships
            RETURN {
                "vertex": v,
                "edges": p.edges
            }
    )
    
    RETURN {
        "center": entity,
        "neighborhood": neighborhood
    }
    """
    
    # Execute with version constraint
    result = connection.execute_query(
        aql_query,
        bind_vars={
            "entity_id": entity_id,
            "hops": hops
        },
        as_of_version=version
    )
    
    if not result.get("success", False) or not result.get("result"):
        logger.error(f"Failed to get subgraph for {entity_id} at version {version}")
        return None
    
    # Add the version to the result for reference
    subgraph = result.get("result")[0]
    subgraph["version"] = version
    
    return subgraph


def create_kg_evolution_visualization(
    version_subgraphs: List[Tuple[str, Dict[str, Any]]],
    entity_id: str,
    output_file: str
):
    """
    Create a visualization of knowledge graph evolution across versions.
    
    Args:
        version_subgraphs: List of (version, subgraph) tuples
        entity_id: Central entity ID
        output_file: Output file path
    """
    num_versions = len(version_subgraphs)
    
    # Create a figure with subplots for each version
    fig, axes = plt.subplots(1, num_versions, figsize=(6*num_versions, 8))
    if num_versions == 1:
        axes = [axes]  # Make it iterable
    
    # Create a graph for each version
    for i, (version, subgraph) in enumerate(version_subgraphs):
        ax = axes[i]
        
        # Create a directed graph
        G = nx.DiGraph()
        
        # Add the central entity
        central_entity = subgraph.get("center", {})
        central_name = central_entity.get("name", "Unknown")
        G.add_node(central_name, node_type="central")
        
        # Add neighborhood entities and edges
        neighborhood = subgraph.get("neighborhood", [])
        for item in neighborhood:
            vertex = item.get("vertex", {})
            vertex_name = vertex.get("name", "Unknown")
            
            # Add the vertex if not already added
            if not G.has_node(vertex_name):
                G.add_node(vertex_name, node_type="neighbor")
            
            # Add edges
            edges = item.get("edges", [])
            for edge in edges:
                from_id = edge.get("_from", "").split("/")[1]
                to_id = edge.get("_to", "").split("/")[1]
                
                # Get entity names instead of IDs
                from_name = central_name if from_id == central_entity.get("_key", "") else vertex_name
                to_name = central_name if to_id == central_entity.get("_key", "") else vertex_name
                
                G.add_edge(from_name, to_name, label=edge.get("type", "related_to"))
        
        # Draw the graph
        pos = nx.spring_layout(G)
        
        # Draw nodes
        node_colors = []
        for node in G.nodes():
            if G.nodes[node].get("node_type") == "central":
                node_colors.append("lightblue")
            else:
                node_colors.append("lightgreen")
        
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=500)
        nx.draw_networkx_labels(G, pos, ax=ax, font_size=8)
        
        # Draw edges
        edge_labels = nx.get_edge_attributes(G, "label")
        nx.draw_networkx_edges(G, pos, ax=ax, arrows=True)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax, font_size=7)
        
        # Set title
        ax.set_title(f"Version: {version}")
        ax.axis("off")
    
    # Add main title
    fig.suptitle(f"Knowledge Graph Evolution: {entity_id}", fontsize=16)
    
    # Add legend
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="lightblue", markersize=10, label="Central Entity"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="lightgreen", markersize=10, label="Neighbor Entity")
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=2)
    
    # Save the visualization
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(output_file)
    plt.close()


def main():
    """Main entry point for the version visualizer CLI."""
    parser = argparse.ArgumentParser(
        description="HADES Knowledge Graph Version Visualizer"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Timeline visualization command
    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Visualize version history as a timeline"
    )
    timeline_parser.add_argument(
        "--collection", 
        required=True,
        help="Collection name"
    )
    timeline_parser.add_argument(
        "--document-id", 
        required=True,
        help="Document ID"
    )
    timeline_parser.add_argument(
        "--output", 
        default="version_timeline.png",
        help="Output file path"
    )
    timeline_parser.set_defaults(func=visualize_version_history)
    
    # Diff visualization command
    diff_parser = subparsers.add_parser(
        "diff", 
        help="Visualize differences between versions"
    )
    diff_parser.add_argument(
        "--collection", 
        required=True,
        help="Collection name"
    )
    diff_parser.add_argument(
        "--document-id", 
        required=True,
        help="Document ID"
    )
    diff_parser.add_argument(
        "--version1", 
        required=True,
        help="First version to compare"
    )
    diff_parser.add_argument(
        "--version2", 
        required=True,
        help="Second version to compare"
    )
    diff_parser.add_argument(
        "--output", 
        default="version_diff.png",
        help="Output file path"
    )
    diff_parser.set_defaults(func=visualize_version_diff)
    
    # KG evolution visualization command
    kg_parser = subparsers.add_parser(
        "kg-evolution", 
        help="Visualize knowledge graph evolution"
    )
    kg_parser.add_argument(
        "--entity-id", 
        required=True,
        help="Entity ID"
    )
    kg_parser.add_argument(
        "--versions", 
        required=True,
        help="Comma-separated list of versions to visualize"
    )
    kg_parser.add_argument(
        "--hops", 
        type=int,
        default=1,
        help="Number of hops to include in the subgraph"
    )
    kg_parser.add_argument(
        "--output", 
        default="kg_evolution.png",
        help="Output file path"
    )
    kg_parser.set_defaults(func=visualize_kg_evolution)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if not HAS_VISUALIZATION:
        logger.error("Visualization requires matplotlib and networkx")
        logger.error("Install with: pip install matplotlib networkx")
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main() 