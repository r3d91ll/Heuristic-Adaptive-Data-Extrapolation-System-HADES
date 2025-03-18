# HADES PathRAG Implementation

## 1. Introduction

This document outlines the comprehensive implementation of PathRAG (Path Retrieval Augmented Generation) within the HADES architecture. PathRAG serves as a crucial component enabling graph-based knowledge retrieval with an emphasis on relational paths between entities. It leverages concepts from the paper "PathRAG: Pruning Graph-based Retrieval Augmented Generation with Relational Paths" (Wu et al., 2024) and incorporates memory management techniques inspired by "MemGPT: Towards LLMs as Operating Systems" (Packer et al., 2023).

### 1.1 Architecture Overview

PathRAG sits at the core of HADES' knowledge retrieval pipeline, positioned between the MCP server and downstream components such as Triple Context Restoration (TCR) and GraphCheck:

```
MCP Server → PathRAG → Triple Context Restoration → LLM Analysis → GraphCheck
```

Its integration enables:
- Graph-based retrieval of contextually relevant knowledge
- Efficient entity and relationship management
- Flow-based path scoring and pruning
- Hierarchical memory management through tiered storage
- Context-aware query processing

## 2. Core PathRAG Implementation

### 2.1 PathRAG Base Class

The `PathRAG` class handles all aspects of graph-based knowledge management:

```python
class PathRAG:
    """
    Path Retrieval-Augmented Generation (PathRAG) module for HADES.
    
    This module handles all aspects of graph-based knowledge management including:
    - Data ingestion/creation of entities and relationships
    - Path-based knowledge retrieval
    - Path pruning and scoring algorithms
    - Version-aware data operations
    """

    def __init__(self):
        """Initialize the PathRAG module."""
        self.db_connection = DBConnection(db_name="hades_graph")
        self.initialized = False
        self.db = None
        self.arango_db = None
        
        # Ensure database connection is established
        try:
            # Get ArangoDB credentials from environment
            self._connect_to_database()
            self._ensure_required_collections()
            self.initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize PathRAG: {e}")
```

### 2.2 Entity and Relationship Model

Following our enhanced entity-relationship model clarity, entities and relationships are structured as:

```python
# Entity Structure
entity = {
    "name": "entity_name",               # Unique identifier
    "entity_type": "concept",            # Type classification
    "domain": "domain_name",             # Knowledge domain
    "observations": ["fact1", "fact2"],  # Atomic observations
    "metadata": {...}                    # Additional properties
}

# Relationship Structure
relationship = {
    "from": "entity_name_1",             # Source entity
    "to": "entity_name_2",               # Target entity 
    "relation_type": "contains",         # Active voice relationship
    "weight": 0.85,                      # Relationship strength
    "metadata": {...}                    # Additional properties
}
```

### 2.3 Path Retrieval

The core path retrieval functionality executes graph traversals to find paths linking entities:

```python
def retrieve_paths(
    self,
    query: str,
    max_paths: int = 5,
    domain_filter: Optional[str] = None,
    as_of_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve paths from the knowledge graph.
    
    Args:
        query: The query to retrieve paths for
        max_paths: Maximum number of paths to retrieve
        domain_filter: Optional domain filter
        as_of_version: Optional version to query against
        
    Returns:
        Retrieved paths and metadata
    """
    # Define AQL query for path retrieval
    aql_query = """
    FOR v, e, p IN 1..5 OUTBOUND 'entities/{query}' edges
        FILTER p.vertices[*].domain ALL == @domain_filter OR NOT @domain_filter
        LIMIT @max_paths
        RETURN {
            "path": CONCAT_SEPARATOR(' -> ', p.vertices[*].name),
            "vertices": p.vertices,
            "edges": p.edges,
            "score": LENGTH(p.vertices)
        }
    """
    
    # Execute query and return results
    paths = self._execute_aql_query(aql_query, 
                                   {"domain_filter": domain_filter, 
                                    "max_paths": max_paths})
    
    return {
        "success": True,
        "query": query,
        "paths": self.prune_paths(paths)
    }
```

### 2.4 Path Scoring and Pruning

The original implementation used simple path length-based scoring:

```python
def calculate_score(self, path: Dict[str, Any]) -> float:
    """
    Calculate a score for a path based on heuristics.
    
    Args:
        path: Path to score
    
    Returns:
        Calculated score
    """
    # Example heuristic: prioritize shorter paths and vertices with higher confidence scores
    path_length = len(path["vertices"])
    confidence_scores = [vertex.get("confidence", 1.0) for vertex in path["vertices"]]
    average_confidence = sum(confidence_scores) / len(confidence_scores)
    
    # Score is a combination of path length and average confidence score
    score = (1 / path_length) * average_confidence
    
    return score
```

### 2.5 Data Ingestion

The `ingest_data` method processes incoming data, creating entities and relationships:

```python
def ingest_data(self, data: List[Dict[str, Any]], domain: str, 
               as_of_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Ingest data into the knowledge graph.
    
    Args:
        data: Data to ingest
        domain: Domain to associate with the data
        as_of_version: Optional version to tag the data with
        
    Returns:
        Status of the ingestion operation
    """
    # Process entities
    entity_result = self._process_entities(data, domain, as_of_version)
    
    # Process relationships
    relationship_result = self._process_relationships(data, domain, as_of_version)
    
    return {
        "success": True,
        "entities_created": entity_result.get("created", 0),
        "relationships_created": relationship_result.get("created", 0)
    }
```

## 3. Memory-Enhanced PathRAG Implementation

### 3.1 Tiered Memory Management

Based on the MemGPT paper, we implement a tiered memory management system that utilizes different storage layers based on access patterns and importance:

```python
class TieredMemoryManager:
    """
    Manages the movement of data between different memory tiers
    based on access patterns and importance.
    """
    
    def __init__(self, config=None):
        """Initialize the tiered memory manager."""
        self.config = config or {
            "ram_cache_size_mb": 8192,
            "nvme_cache_path": "/home/todd/.cache/hades_pathrag",
            "nvme_cache_size_gb": 50,
        }
        
        # Initialize memory tiers
        self.ram_cache = LRUCache(max_size_mb=self.config["ram_cache_size_mb"])
        self.disk_cache = DiskCache(
            cache_path=self.config["nvme_cache_path"],
            max_size_gb=self.config["nvme_cache_size_gb"]
        )
        
        # Database reference for slowest tier
        self.db = None
    
    def get(self, key: str, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        Get data from the tiered memory system.
        Checks RAM first, then disk, then database.
        
        Args:
            key: The key to retrieve
            context: Optional context information to help with retrieval
            
        Returns:
            Retrieved data or None if not found
        """
        # Check RAM cache first (fastest tier)
        data = self.ram_cache.get(key)
        if data is not None:
            return data
            
        # Check disk cache next (middle tier)
        data = self.disk_cache.get(key)
        if data is not None:
            # Promote to RAM cache if found on disk
            importance = self._calculate_importance(data, context)
            self.ram_cache.put(key, data, importance)
            return data
            
        # Finally check database (slowest tier)
        if self.db is not None:
            data = self._fetch_from_database(key)
            if data is not None:
                # Add to appropriate caches based on importance
                importance = self._calculate_importance(data, context)
                if importance > 0.5:  # Higher importance goes to RAM
                    self.ram_cache.put(key, data, importance)
                else:  # Lower importance just goes to disk
                    self.disk_cache.put(key, data)
                return data
                
        return None
    
    def put(self, key: str, data: Any, importance: float = 0.5,
           context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data in the tiered memory system.
        Placement depends on importance and size.
        
        Args:
            key: The key to store
            data: The data to store
            importance: Importance score (0.0-1.0)
            context: Optional context information
            
        Returns:
            Success status
        """
        if importance > 0.5:  # Higher importance goes to RAM
            self.ram_cache.put(key, data, importance)
        
        # Always store in disk cache for persistence
        self.disk_cache.put(key, data)
        
        return True
```

### 3.2 Enhanced Path Scoring Algorithm

We implement a flow-based path scoring algorithm as described in the PathRAG paper:

```python
def calculate_path_score(self, path, source_node, decay_rate=0.85):
    """
    Calculate the reliability score for a path using flow-based methods.
    Implements the algorithm described in the PathRAG paper.
    
    Args:
        path: Path object to score
        source_node: Source node for the path
        decay_rate: Decay rate for resource flow (default: 0.85)
        
    Returns:
        Reliability score between 0 and 1
    """
    # Default score based on path length if path data is incomplete
    if not path or "vertices" not in path or not path["vertices"]:
        return 0.1
        
    # For paths with no edges information, fall back to simple length-based scoring
    if "edges" not in path or not path["edges"]:
        return 0.3 / max(1, len(path["vertices"]) - 1)
        
    # Initialize the resource at the source node
    if not source_node:
        source_node = path["vertices"][0]
        
    resource = {source_node.get("_id", "start"): 1.0}
    path_score = 0.0
    
    # Process each edge in the path to calculate resource flow
    for i, edge in enumerate(path["edges"]):
        from_id = edge.get("_from", "unknown")
        to_id = edge.get("_to", "unknown")
        
        # Skip if the from_node has no resource
        if from_id not in resource:
            continue
        
        # Calculate resource flow with decay penalty
        edge_weight = edge.get("weight", 1.0)
        flow = resource[from_id] * edge_weight * (decay_rate ** i)
        
        # Add to receiving node's resource
        resource[to_id] = resource.get(to_id, 0) + flow
        
        # Add to path score
        path_score += flow
    
    # Normalize by path length for fair comparison
    return path_score / max(1, len(path["edges"]))
```

### 3.3 Context Window Management

To optimize LLM context usage, we introduce a context window manager inspired by MemGPT:

```python
class ContextWindowManager:
    """
    Manages the LLM context window by optimizing the content to fit
    within token limits while preserving the most relevant information.
    """
    def __init__(self, max_tokens=4096, reserve_tokens=512):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens
        self.available_tokens = max_tokens - reserve_tokens
        
        # Context sections ordered by priority
        self.context = {
            "high_priority": [],   # Critical paths, recent context
            "medium_priority": [], # Supporting paths, domain knowledge
            "low_priority": []     # Background knowledge, fallback info
        }
        
        self.current_token_count = 0
    
    def add_path(self, path, priority="medium_priority"):
        """Add a path to the context window with specified priority."""
        # Convert path to text and count tokens
        path_text = self._path_to_text(path)
        token_count = self._count_tokens(path_text)
        
        # Check if adding this would exceed our limit
        if self.current_token_count + token_count > self.available_tokens:
            # Need to make space by evicting lower priority items
            self._make_space(token_count)
            
        # Add path if space available
        if self.current_token_count + token_count <= self.available_tokens:
            self.context[priority].append({
                "text": path_text,
                "tokens": token_count,
                "reliability": path.get("reliability", 0.5)
            })
            self.current_token_count += token_count
            return True
        
        return False
    
    def get_formatted_context(self):
        """
        Get the formatted context for LLM prompts.
        Follows MemGPT's principle by placing high priority content
        at the beginning and end of the context.
        """
        sections = []
        
        # Add high priority at the beginning
        for item in self.context["high_priority"]:
            sections.append(item["text"])
            
        # Add medium priority in the middle
        for item in self.context["medium_priority"]:
            sections.append(item["text"])
            
        # Add low priority at the end
        for item in self.context["low_priority"]:
            sections.append(item["text"])
            
        return "\n\n".join(sections)
```

### 3.4 Memory-Enhanced PathRAG Class

We integrate all these enhancements into a `MemoryEnhancedPathRAG` class that extends the base implementation:

```python
class MemoryEnhancedPathRAG(PathRAG):
    """
    Enhancement of the base PathRAG with memory management
    and improved path retrieval algorithms.
    """
    
    def __init__(self, config=None):
        """Initialize the memory-enhanced PathRAG module."""
        super().__init__()
        
        # Default configuration
        self.config = config or {
            "decay_rate": 0.85,
            "pruning_threshold": 0.01,
            "enable_caching": True,
            "ram_cache_size_mb": 8192,
            "nvme_cache_path": "/home/todd/.cache/hades_pathrag",
            "nvme_cache_size_gb": 50,
            "context_window_tokens": 4096,
            "reserve_tokens": 512,
        }
        
        # Initialize memory management components
        if self.config["enable_caching"]:
            self.memory_manager = TieredMemoryManager({
                "ram_cache_size_mb": self.config["ram_cache_size_mb"],
                "nvme_cache_path": self.config["nvme_cache_path"],
                "nvme_cache_size_gb": self.config["nvme_cache_size_gb"],
            })
            self.memory_manager.db = self.db
            
        # Initialize context window management
        self.context_manager = ContextWindowManager(
            max_tokens=self.config["context_window_tokens"],
            reserve_tokens=self.config["reserve_tokens"]
        )
        
        # Track recent queries for context-aware retrieval
        self.recent_queries = collections.deque(maxlen=10)
    
    def retrieve_paths(self, query, max_paths=5, domain_filter=None, as_of_version=None):
        """
        Enhanced path retrieval with caching and flow-based pruning.
        Maintains the same API as the original implementation.
        """
        # Add to recent queries for context awareness
        self.recent_queries.append(query)
        
        # Generate cache key
        cache_params = json.dumps({
            "max_paths": max_paths,
            "domain_filter": domain_filter,
            "as_of_version": as_of_version
        })
        cache_key = f"path:{query}:{cache_params}"
        
        # Check cache if enabled
        if self.config["enable_caching"] and hasattr(self, 'memory_manager'):
            context = {"recent_queries": list(self.recent_queries)}
            cached_result = self.memory_manager.get(cache_key, context)
            if cached_result:
                return cached_result
        
        # Cache miss, perform database query
        base_result = super().retrieve_paths(query, max_paths * 2, domain_filter, as_of_version)
        
        if not base_result.get("success", False):
            return base_result
            
        # Apply flow-based pruning to the retrieved paths
        raw_paths = base_result.get("paths", [])
        
        # Calculate reliability scores
        for path in raw_paths:
            path["reliability"] = self.calculate_path_score(
                path, 
                path["vertices"][0] if "vertices" in path and path["vertices"] else None,
                self.config["decay_rate"]
            )
        
        # Prune paths based on threshold
        pruned_paths = [p for p in raw_paths if p.get("reliability", 0) >= self.config["pruning_threshold"]]
        
        # Sort by reliability and limit to requested number
        pruned_paths = sorted(pruned_paths, key=lambda p: p.get("reliability", 0), reverse=True)
        pruned_paths = pruned_paths[:max_paths]
        
        result = {
            "success": True,
            "query": query,
            "paths": pruned_paths,
            "count": len(pruned_paths),
            "pruned_from": len(raw_paths)
        }
        
        # Cache the result
        if self.config["enable_caching"] and hasattr(self, 'memory_manager'):
            importance = 0.7 if len(pruned_paths) > 0 else 0.3
            self.memory_manager.put(cache_key, result, importance, 
                                   {"recent_queries": list(self.recent_queries)})
            
        return result
        
    def format_paths_for_prompt(self, paths, query):
        """
        Order paths by reliability for optimal LLM consumption.
        Addresses the "lost in the middle" issue identified in PathRAG.
        """
        # Sort paths by reliability (ascending)
        sorted_paths = sorted(paths, key=lambda p: p.get("reliability", 0))
        
        # Format prompt with query at beginning
        prompt = f"Query: {query}\n\nRelevant information:\n\n"
        
        # Add medium reliability paths first (middle of the prompt)
        middle_paths = sorted_paths[:-1] if len(sorted_paths) > 1 else []
        for path in middle_paths:
            path_text = f"Path ({path.get('reliability', 0):.2f}): {path.get('path', 'Unknown')}\n"
            for vertex in path.get("vertices", []):
                path_text += f"  - {vertex.get('name', 'Entity')}: {vertex.get('description', '')}\n"
            prompt += path_text + "\n"
        
        # Add the most reliable path last (golden memory region)
        if sorted_paths:
            most_reliable = sorted_paths[-1]
            prompt += f"Most relevant path ({most_reliable.get('reliability', 0):.2f}): {most_reliable.get('path', 'Unknown')}\n"
            for vertex in most_reliable.get("vertices", []):
                prompt += f"  - {vertex.get('name', 'Entity')}: {vertex.get('description', '')}\n"
        
        return prompt
        
    def retrieve_and_format(self, query, max_paths=5, domain_filter=None, as_of_version=None):
        """
        Retrieve paths and format them for LLM prompting in one step.
        """
        result = self.retrieve_paths(query, max_paths, domain_filter, as_of_version)
        
        if not result.get("success", False):
            return f"Error retrieving paths: {result.get('error', 'Unknown error')}"
            
        paths = result.get("paths", [])
        if not paths:
            return f"No paths found for query: {query}"
            
        return self.format_paths_for_prompt(paths, query)
```

## 4. MCP Server Integration

The PathRAG functionality is exposed through the MCP server, which provides tool-based access for LLMs and client applications:

```python
async def pathrag_retrieve(self, params: Dict[str, Any], session_data: Dict[str, Any]):
    """
    Tool handler to retrieve paths using PathRAG.
    
    Args:
        params: Parameters for the tool including:
            - query: The query to retrieve paths for
            - max_paths: Maximum number of paths to retrieve
            - domain_filter: Optional domain filter
            - as_of_version: Optional version to query against
            - format_for_llm: Optional flag to return formatted prompt
        session_data: Session data including authentication info
        
    Returns:
        Dict containing the retrieved paths and metadata
    """
    # Check authentication
    if not session_data.get("authenticated", False):
        return {
            "success": False,
            "error": "Not authenticated"
        }
    
    # Extract parameters
    query = params.get("query", "")
    max_paths = params.get("max_paths", 5)
    domain_filter = params.get("domain_filter")
    as_of_version = params.get("as_of_version")
    format_for_llm = params.get("format_for_llm", False)
    
    # Validate parameters
    if not query:
        return {
            "success": False,
            "error": "Query is required"
        }
    
    # Initialize Memory-Enhanced PathRAG if available, otherwise use base PathRAG
    try:
        try:
            from src.rag.memory_enhanced_path_rag import MemoryEnhancedPathRAG
            path_rag = MemoryEnhancedPathRAG()
            use_enhanced = True
        except ImportError:
            from src.rag.path_rag import PathRAG
            path_rag = PathRAG()
            use_enhanced = False
        
        # Call the appropriate method based on format_for_llm flag
        if format_for_llm and use_enhanced:
            result = path_rag.retrieve_and_format(
                query=query,
                max_paths=max_paths,
                domain_filter=domain_filter,
                as_of_version=as_of_version
            )
            return {
                "success": True,
                "formatted_prompt": result
            }
        else:
            # Standard path retrieval
            result = path_rag.retrieve_paths(
                query=query,
                max_paths=max_paths,
                domain_filter=domain_filter,
                as_of_version=as_of_version
            )
            return result
            
    except Exception as e:
        logger.error(f"Error retrieving paths: {e}")
        return {
            "success": False,
            "error": f"Error retrieving paths: {str(e)}"
        }
```

## 5. Implementation Plan

### 5.1 Phase 1: Core Functionality (Week 1)

1. **Base PathRAG Implementation**
   - Implement entity and relationship data modeling
   - Set up basic path retrieval with ArangoDB
   - Create initial path scoring based on path length

2. **MCP Server Integration**
   - Expose PathRAG tools through the MCP server
   - Implement authentication and parameter validation
   - Create basic API documentation

### 5.2 Phase 2: Flow-Based Path Scoring (Week 2)

1. **Resource Flow Algorithm**
   - Implement flow-based path scoring as described in the PathRAG paper
   - Add decay rate for resource flow through edges
   - Update the pruning algorithm to use reliability scores

2. **Enhanced AQL Queries**
   - Modify AQL queries to retrieve edge weights
   - Add support for domain filtering
   - Implement version-aware queries

### 5.3 Phase 3: Memory Management (Week 3)

1. **Tiered Memory System**
   - Implement LRU cache for RAM-based caching
   - Create disk cache for NVMe-based storage
   - Develop the TieredMemoryManager to coordinate between tiers

2. **Context Window Management**
   - Implement token counting and budget management
   - Create priority-based context organization
   - Add support for "golden memory region" placement

### 5.4 Phase 4: Integration and Optimization (Week 4)

1. **MemoryEnhancedPathRAG Implementation**
   - Create the extended PathRAG class with all enhancements
   - Ensure backward compatibility
   - Implement the retrieve_and_format convenience method

2. **Testing and Performance Tuning**
   - Benchmark path retrieval with and without caching
   - Optimize configuration parameters
   - Document performance characteristics

## 6. Conclusion

This implementation of PathRAG combines the research insights from the PathRAG paper with memory management techniques from MemGPT to create a powerful, efficient graph-based knowledge retrieval system. It maintains backward compatibility with the existing HADES architecture while introducing significant enhancements to path retrieval quality and performance.

The key improvements include:

1. **Flow-based path scoring** - More accurately identifies relevant paths based on resource flow
2. **Tiered memory management** - Optimizes data access across RAM and disk storage
3. **Context window optimization** - Maximizes the utility of limited LLM context space
4. **Strategic prompt formatting** - Addresses the "lost in the middle" phenomenon for better LLM responses

These enhancements align with HADES' goal of efficient single-system MI that maximizes resource utilization and delivers accurate, multi-hop answers through graph-based knowledge retrieval.

## 7. References

1. Wu, X., Zhang, Y., Feng, Y., Wang, D., Wang, H., Lai, C., Fang, M., Chen, R., Lim, E., Su, J., Zheng, N., & Chua, T. (2024). "PathRAG: Pruning Graph-based Retrieval Augmented Generation with Relational Paths." arXiv:2502.14902.

2. Packer, C., Wooders, S., Lin, K., Fang, V., Patil, S. G., Stoica, I., & Gonzalez, J. E. (2023). "MemGPT: Towards LLMs as Operating Systems." arXiv:2310.08560.

3. Liu, N., Zhang, Z., Yu, W., Wang, H., Cheng, H., Zhuang, Y., Cheng, Y., Lin, L., Lu, S., & Chen, X. (2024). "Lost in the Middle: How Language Models Use Long Contexts."
