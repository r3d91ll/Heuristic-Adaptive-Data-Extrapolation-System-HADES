"""Context analyzer service."""

import logging
from typing import Dict, Any, List

from hades.core.models import ContextMetadata, AllocationDecision
from hades.core.exceptions import MCPError

logger = logging.getLogger(__name__)

class ContextAnalyzer:
    """Analyzes context for memory allocation."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize context analyzer."""
        self.config = config
        self.elysium_capacity = config.get("elysium_capacity", 1000)
        self.asphodel_window = config.get("asphodel_window", 2000)
        self.lethe_threshold = config.get("lethe_threshold", 0.5)

    async def analyze(self, context: str) -> ContextMetadata:
        """Analyze context and extract metadata."""
        try:
            tokens = self._tokenize(context)
            semantics = await self._extract_semantics(context)
            relationships = await self._identify_relationships(context)
            
            return ContextMetadata(
                tokens=tokens,
                semantics=semantics,
                relationships=relationships
            )
        except Exception as e:
            logger.error("Context analysis failed: %s", e, exc_info=True)
            raise MCPError(
                "ANALYSIS_ERROR",
                f"Context analysis failed: {e}"
            )

    async def allocate(self, metadata: ContextMetadata) -> AllocationDecision:
        """Determine optimal memory allocation."""
        try:
            if self._is_critical(metadata):
                return AllocationDecision(realm="elysium", priority="high")
            elif self._is_active(metadata):
                return AllocationDecision(realm="asphodel", priority="medium")
            else:
                return AllocationDecision(realm="tartarus", priority="low")
        except Exception as e:
            logger.error("Allocation decision failed: %s", e, exc_info=True)
            raise MCPError(
                "ALLOCATION_ERROR",
                f"Allocation decision failed: {e}"
            )

    def _tokenize(self, context: str) -> List[str]:
        """Tokenize context."""
        return context.split()

    async def _extract_semantics(self, context: str) -> Dict[str, Any]:
        """Extract semantic information from context."""
        return {"relevance": 0.8 if len(context) > 100 else 0.3}

    async def _identify_relationships(self, context: str) -> List[Dict[str, str]]:
        """Identify relationships in context."""
        # Basic relationship identification based on word proximity
        words = context.split()
        relationships = []
        
        for i in range(len(words) - 1):
            relationships.append({
                "type": "sequence",
                "source": words[i],
                "target": words[i + 1],
                "weight": "1.0"
            })
        
        return relationships

    def _is_critical(self, metadata: ContextMetadata) -> bool:
        """Check if context is critical."""
        return (
            len(metadata.tokens) <= self.elysium_capacity and
            metadata.semantics.get("relevance", 0) > self.lethe_threshold
        )

    def _is_active(self, metadata: ContextMetadata) -> bool:
        """Check if context is active."""
        return (
            len(metadata.tokens) <= self.asphodel_window and
            metadata.semantics.get("relevance", 0) > 0.3
        ) 