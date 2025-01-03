"""Data models for HADES."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
import numpy as np
import uuid


class QueryArgs(BaseModel):
    """Query arguments."""

    query: str = Field(..., description="AQL query string")
    bind_vars: Optional[Dict[str, Any]] = Field(default=None, description="Query bind variables")

    @field_validator("query")
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty."""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v


class VectorSearchArgs(BaseModel):
    """Vector search arguments."""

    collection: str = Field(..., description="Collection name")
    vector: List[float] = Field(..., description="Query vector")
    top_k: int = Field(10, description="Number of results to return")

    @field_validator("vector")
    def validate_vector(cls, v: List[float]) -> List[float]:
        """Validate vector is not empty."""
        if not v:
            raise ValueError("Vector cannot be empty")
        return v

    @field_validator("top_k")
    def validate_top_k(cls, v: int) -> int:
        """Validate top_k is positive."""
        if v <= 0:
            raise ValueError("top_k must be positive")
        return v


class HybridSearchArgs(BaseModel):
    """Hybrid search arguments."""

    collection: str = Field(..., description="Collection name")
    vector: List[float] = Field(..., description="Query vector")
    filter_query: str = Field(..., description="Filter query")
    bind_vars: Optional[Dict[str, Any]] = Field(default=None, description="Query bind variables")
    top_k: int = Field(10, description="Number of results to return")

    @field_validator("vector")
    def validate_vector(cls, v: List[float]) -> List[float]:
        """Validate vector is not empty."""
        if not v:
            raise ValueError("Vector cannot be empty")
        return v

    @field_validator("top_k")
    def validate_top_k(cls, v: int) -> int:
        """Validate top_k is positive."""
        if v <= 0:
            raise ValueError("top_k must be positive")
        return v


class CallToolRequest(BaseModel):
    """Call tool request."""

    tool_name: str = Field(..., description="Tool name")
    args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")

    @field_validator("tool_name")
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name is not empty."""
        if not v.strip():
            raise ValueError("Tool name cannot be empty")
        return v


class ListToolsRequest(BaseModel):
    """List tools request.""" 


class ContextMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tokens: List[str]
    semantics: Dict[str, float]
    relationships: List[Dict[str, str]]


class AllocationDecision(BaseModel):
    realm: str = Field(..., description="Target memory realm (elysium/asphodel/tartarus)")
    priority: str = Field(..., description="Priority level (high/medium/low)")


class ElysiumRealm(BaseModel):
    capacity: int = Field(..., description="Maximum number of tokens to preserve (n_keep)")
    preserved_context: Dict[str, Dict] = Field(default_factory=dict)

    def __setitem__(self, key: str, value: Dict) -> None:
        """Support item assignment for context storage."""
        self.preserved_context[key] = value

    async def preserve(self, context: str) -> bool:
        """Preserve critical context in n_keep region."""
        tokens = context.split()  # Simple tokenization for now
        if len(tokens) <= self.capacity:
            self.preserved_context[str(uuid.uuid4())] = {"tokens": tokens}
            return True
        return False


class AsphodelRealm(BaseModel):
    window_size: int = Field(..., description="Size of active context window")
    active_context: Dict[str, Dict] = Field(default_factory=dict)
    message_order: List[str] = Field(default_factory=list)  # List of message IDs in order
    computation_cache: Dict = Field(default_factory=dict)

    def __setitem__(self, key: str, value: Dict) -> None:
        """Support item assignment for context storage."""
        self.active_context[key] = value
        if key not in self.message_order:
            self.message_order.append(key)

    async def process(self, message: str) -> None:
        """Process new messages in working memory."""
        msg_id = str(uuid.uuid4())
        self.active_context[msg_id] = {"message": message, "tokens": message.split()}
        self.message_order.append(msg_id)
        
        # If we've exceeded the window size, remove the oldest message(s)
        while len(self.active_context) > self.window_size:
            oldest_key = self.message_order.pop(0)  # Remove and get the oldest message ID
            del self.active_context[oldest_key]


class TartarusRealm(BaseModel):
    archive: Dict[str, Dict] = Field(default_factory=dict)
    relationship_graph: Dict[str, List[str]] = Field(default_factory=dict)

    def __setitem__(self, key: str, value: Dict) -> None:
        """Support item assignment for context storage."""
        self.archive[key] = value

    async def archive_context(self, context: ContextMetadata) -> str:
        """Archive context with semantic indexing."""
        context_id = str(uuid.uuid4())
        self.archive[context_id] = context.model_dump()
        return context_id


class StyxController(BaseModel):
    elysium: ElysiumRealm
    asphodel: AsphodelRealm
    tartarus: TartarusRealm

    async def manage_flow(self, context: str, metadata: ContextMetadata) -> None:
        """Manage context flow between memory realms."""
        if self._should_preserve(context):
            await self.elysium.preserve(context)
        elif self._is_active(context):
            await self.asphodel.process(context)
        else:
            await self.tartarus.archive_context(metadata)

    def _should_preserve(self, context: str) -> bool:
        """Determine if context should be preserved in Elysium."""
        tokens = context.split()
        # Only preserve very short, critical contexts (1-2 tokens)
        return len(tokens) <= 2 and len(tokens) <= self.elysium.capacity

    def _is_active(self, context: str) -> bool:
        """Determine if context is part of active conversation."""
        return True  # Default to active for now


class LetheManager(BaseModel):
    threshold: float = Field(0.5, description="Relevance threshold for forgetting")

    async def forget(self, context_id: str, tartarus: TartarusRealm) -> None:
        """Implement controlled forgetting of irrelevant context."""
        if context_id in tartarus.archive:
            relevance = await self._assess_relevance(context_id, tartarus)
            if relevance < self.threshold:
                del tartarus.archive[context_id]

    async def _assess_relevance(self, context_id: str, tartarus: TartarusRealm) -> float:
        """Assess the relevance of archived context."""
        # Simple relevance scoring for now
        return np.random.random()  # Placeholder for actual relevance calculation 