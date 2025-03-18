# HADES Embedded Context Layer (ECL) User Memory Implementation

## Overview

The Embedded Context Layer (ECL) in HADES will be enhanced with user memory capabilities inspired by the MCP memory server. This document outlines the planned implementation of the user memory system, focusing on filesystem-based memory storage, integration with the MCP server, and adaptation to the enhanced entity-relationship model.

## 1. User Memory Architecture

### 1.1 Directory Structure

The ECL user memory system will use a hierarchical directory structure under `/home/hades/.hades` to store user data:

```
/home/hades/.hades/
├── users/                  # User-specific directories (hashed by API key)
│   └── <user_hash>/        # Individual user directory
│       ├── observations/   # User observations
│       │   └── obs_{timestamp}.txt
│       └── conversations/  # User conversations
│           └── <conv_id>/
│               ├── raw/    # Raw conversation data
│               │   └── messages.jsonl
│               └── metadata/ # Conversation metadata
│                   └── context.json
└── system/                 # System-level information
    ├── passwd/             # User account information
    │   ├── raw/            # Raw files
    │   │   └── etc_passwd.txt
    │   └── metadata/       # Processed information
    │       └── permissions.json
    └── groups/             # Group information
        ├── raw/
        │   └── etc_group.txt
        └── metadata/
            └── relationships.json
```

### 1.2 User Memory Types

The ECL will support two primary types of user memory:

1. **Observations**: Discrete facts or notes about the user's preferences, behaviors, or context
2. **Conversations**: Complete conversation histories with metadata for context preservation

## 2. Implementation Components

### 2.1 UserMemoryManager Class

The `UserMemoryManager` class will handle:

- Secure storage of user memory using API key hashing
- File-based organization of memories
- System information monitoring (users, groups)
- Observation and conversation management

### 2.2 MCP Server Integration

The ECL user memory system will be integrated with the MCP server through dedicated tools:

- `get_user_memory`: Retrieve memories relevant to the current context
- `add_user_observation`: Add new observations about the user
- `create_conversation`: Create a new conversation context
- `add_conversation_message`: Add messages to existing conversations

### 2.3 PathRAG Integration

The ECL user memory system will leverage PathRAG to:

- Query across user memory directories
- Provide relevant context from past observations and conversations
- Incorporate user memory into entity-relationship structures

## 3. Entity-Relationship Model for User Memory

### 3.1 ArangoDB Schema Enhancements

The user memory system will use an enhanced ArangoDB schema that supports:

- Typed entities with atomic observations
- Explicit directional relationships
- Vector embedding for semantic retrieval

### 3.2 Entity Model

User observations will be represented as entities with:

- `name`: Unique identifier
- `entity_type`: Classification (preference, habit, context, etc.)
- `observations`: List of atomic observations
- `embedding`: Vector representation for similarity search
- `metadata`: Additional structured data

### 3.3 Relation Model

Relationships between entities will be represented with:

- `from_entity`: Source entity name
- `to_entity`: Target entity name
- `relation_type`: Active voice relationship type
- `metadata`: Additional context for the relationship

## 4. Implementation Phases

### Phase 1: Core Infrastructure
- Implement `UserMemoryManager` class
- Set up directory structure and file handling
- Implement system monitoring components

### Phase 2: MCP Integration
- Add user memory retrieval tools to MCP server
- Implement observation and conversation management tools
- Test authentication and session data handling

### Phase 3: Entity-Relationship Integration
- Enhance PathRAG to work with filesystem-based memory
- Develop entity extraction from user observations
- Implement relation identification between memory entities

### Phase 4: Optimization
- Add caching for frequent memory access
- Implement memory consolidation for efficient retrieval
- Add memory decay or priority mechanisms

## 5. Security Considerations

- API keys will be hashed before use in directory names
- File permissions will be restricted to the HADES service user
- User memories will be isolated in individual directories
- Authentication will be required for all memory access

## 6. Extended Capabilities

Future enhancements may include:

- User memory summarization
- Time-based memory retrieval prioritization
- Automatic entity extraction from conversations
- Cross-user pattern identification (with appropriate privacy controls)
- Memory conflict resolution strategies

## 7. Integration with Embedded Models

The ECL user memory system will leverage the embedded LLMs to:

- Extract entities from user observations
- Identify relationships between entities
- Generate context from relevant memories
- Classify and categorize observations for better retrieval

---

*Note: This document outlines the planned ECL user memory implementation and will be expanded upon during the actual implementation phase.*
