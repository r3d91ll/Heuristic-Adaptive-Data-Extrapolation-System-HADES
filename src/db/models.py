from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class Observation(BaseModel):
    """
    An observation about an entity.
    
    Attributes:
        content: The content of the observation
        timestamp: The time when the observation was made
        source: Optional source of the observation
    """
    content: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    source: Optional[str] = None

class Entity(BaseModel):
    """
    An entity in the knowledge graph.
    
    Attributes:
        name: The name of the entity
        entity_type: The type of entity (e.g., 'person', 'organization', 'concept')
        observations: List of observations about the entity
        embedding: Optional vector embedding for the entity
        metadata: Optional additional metadata
    """
    name: str
    entity_type: str = Field(..., alias="entityType")
    observations: List[str] = []
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class Relation(BaseModel):
    """
    A relation between two entities in the knowledge graph.
    
    Attributes:
        from_entity: The name of the source entity
        to_entity: The name of the target entity
        relation_type: The type of relation
        metadata: Optional additional metadata
    """
    from_entity: str = Field(..., alias="from")
    to_entity: str = Field(..., alias="to")
    relation_type: str = Field(..., alias="relationType")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ConversationMessage(BaseModel):
    """
    A message in a conversation.
    
    Attributes:
        role: The role of the message sender (e.g., 'user', 'assistant')
        content: The content of the message
        timestamp: The time when the message was sent
    """
    role: str
    content: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())

class Conversation(BaseModel):
    """
    A conversation between a user and the system.
    
    Attributes:
        id: The unique identifier for the conversation
        user_id: The ID of the user
        messages: List of messages in the conversation
        created_at: When the conversation was created
        last_updated: When the conversation was last updated
    """
    id: str
    user_id: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    last_updated: float = Field(default_factory=lambda: datetime.now().timestamp())
