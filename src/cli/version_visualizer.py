from typing import Any, Dict, List, Optional
import logging
from src.db.connection import DBConnection
import plotly.express as px
import pandas as pd

logger = logging.getLogger(__name__)

class VersionVisualizer:
    """
    Version visualization module for HADES.
    
    This module provides visualizations of the knowledge graph versions.
    """

    def __init__(self):
        """Initialize the VersionVisualizer module."""
        logger.info("Initializing VersionVisualizer module")
        self.db_connection = DBConnection()
    
    def visualize_versions(self) -> Dict[str, Any]:
        """
        Visualize the history of knowledge graph versions.
        
        Returns:
            Visualization data and metadata
        """
        logger.info("Visualizing versions")
        
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
            logger.info(f"Retrieved {len(versions)} versions for visualization")
            
            if not versions:
                logger.warning("No versions found to visualize")
                return {
                    "success": True,
                    "version_history": [],
                    "visualization": ""
                }
            
            # Convert the list of dictionaries to a DataFrame
            df = pd.DataFrame(versions)
            
            # Ensure 'timestamp' is in datetime format for plotting
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create a line plot using Plotly Express
            fig = px.line(df, x='timestamp', y='version', title='Knowledge Graph Version History')
            fig.update_xaxes(title_text='Timestamp')
            fig.update_yaxes(title_text='Version')
            
            # Convert the figure to HTML for embedding in web applications
            version_history_html = fig.to_html(full_html=False)
            
            logger.info("Versions visualized successfully")
            return {
                "success": True,
                "version_history": versions,
                "visualization": version_history_html
            }
        
        except Exception as e:
            logger.exception("An error occurred while visualizing versions")
            return {
                "success": False,
                "error": str(e)
            }