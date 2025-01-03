"""Memory allocator service."""

import logging
from typing import Dict, Any

from hades.core.models import (
    ContextMetadata, 
    AllocationDecision,
    ElysiumRealm,
    AsphodelRealm,
    TartarusRealm,
    LetheManager,
    StyxController
)
from hades.core.exceptions import MCPError
from hades.services.context_analyzer import ContextAnalyzer

logger = logging.getLogger(__name__)

class MemoryAllocator:
    """Memory allocator service."""

    def __init__(
        self,
        elysium_capacity: int,
        asphodel_window: int,
        lethe_threshold: float
    ):
        """Initialize memory allocator."""
        self.elysium = ElysiumRealm(capacity=elysium_capacity)
        self.asphodel = AsphodelRealm(window_size=asphodel_window)
        self.tartarus = TartarusRealm()
        self.styx = StyxController(
            elysium=self.elysium,
            asphodel=self.asphodel,
            tartarus=self.tartarus
        )
        self.lethe = LetheManager(threshold=lethe_threshold)
        self.context_analyzer = ContextAnalyzer({
            "elysium_capacity": elysium_capacity,
            "asphodel_window": asphodel_window,
            "lethe_threshold": lethe_threshold
        })

    async def allocate(self, context: str, metadata: ContextMetadata) -> AllocationDecision:
        """Allocate context to appropriate realm."""
        # Determine allocation based on token count and relevance
        token_count = len(metadata.tokens)
        relevance = metadata.semantics.get("relevance", 0.0)

        # Call styx to manage flow
        await self.styx.manage_flow(context, metadata)

        if token_count <= self.elysium.capacity and relevance >= 0.7:
            return AllocationDecision(realm="elysium", priority="high")
        elif relevance >= 0.5:
            return AllocationDecision(realm="asphodel", priority="medium")
        else:
            return AllocationDecision(realm="tartarus", priority="low")

    async def _handle_elysium_allocation(self, context: str, metadata: ContextMetadata) -> None:
        """Handle allocation to Elysium realm."""
        self.elysium[metadata.id] = {
            "context": context,
            "metadata": metadata
        }

    async def _handle_asphodel_allocation(self, context: str, metadata: ContextMetadata) -> None:
        """Handle allocation to Asphodel realm."""
        self.asphodel[metadata.id] = {
            "context": context,
            "metadata": metadata
        }

    async def _handle_tartarus_allocation(self, context: str, metadata: ContextMetadata) -> None:
        """Handle allocation to Tartarus realm."""
        self.tartarus[metadata.id] = {
            "context": context,
            "metadata": metadata
        }

    async def cleanup(self) -> None:
        """Clean up old contexts."""
        try:
            await self._cleanup_old_contexts()
        except Exception as e:
            logger.error("Memory cleanup failed: %s", e, exc_info=True)
            raise MCPError(
                "CLEANUP_ERROR",
                f"Memory cleanup failed: {e}"
            )

    async def _cleanup_old_contexts(self) -> None:
        """Clean up old contexts from Tartarus."""
        # Create a list of keys to avoid dictionary size change during iteration
        context_ids = list(self.tartarus.archive.keys())
        for context_id in context_ids:
            await self.lethe.forget(context_id, self.tartarus)

    async def get_context_stats(self) -> Dict[str, Any]:
        """Get memory context statistics."""
        try:
            return {
                "elysium_used": len(self.elysium.preserved_context),
                "elysium_capacity": self.elysium.capacity,
                "asphodel_used": len(self.asphodel.active_context),
                "asphodel_capacity": self.asphodel.window_size,
                "tartarus_archived": len(self.tartarus.archive)
            }
        except Exception as e:
            logger.error("Failed to get context stats: %s", e, exc_info=True)
            raise MCPError(
                "STATS_ERROR",
                f"Failed to get context stats: {e}"
            ) 