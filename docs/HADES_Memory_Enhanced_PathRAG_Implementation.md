# HADES Memory-Enhanced PathRAG Implementation

## 1. Introduction and Background

This document outlines enhancements to the existing PathRAG implementation in HADES, drawing inspiration from two significant research papers: "PathRAG: Pruning Graph-based Retrieval Augmented Generation with Relational Paths" (Wu et al., 2024) and "MemGPT: Towards LLMs as Operating Systems" (Packer et al., 2023). These refinements aim to improve the performance, efficiency, and contextual awareness of HADES without replacing the current architecture.

### 1.1 Research Foundations

**PathRAG** (Wu et al., 2024) introduces sophisticated graph-based retrieval methods that prioritize key relational paths and reduce redundancy in retrieved information. Its flow-based pruning algorithm with distance awareness enhances the logicality and coherence of generated responses by intelligently selecting the most relevant paths in a knowledge graph.

**MemGPT** (Packer et al., 2023) addresses the limited context window problem in Large Language Models (LLMs) by implementing a hierarchical memory management system inspired by operating system design. It enables extended context handling through tiered storage and intelligent data movement between memory layers.

### 1.2 Current HADES Implementation

The existing HADES system already implements a solid foundation for PathRAG with:

- A graph-based knowledge representation using ArangoDB
- Entity and relationship management with proper metadata
- Basic path traversal and retrieval capabilities
- Integration with the MCP server for tool-based access

### 1.3 Enhancement Goals

These enhancements aim to:

1. Refine path retrieval with flow-based pruning algorithms from PathRAG
2. Implement tiered memory management inspired by MemGPT
3. Optimize context window utilization for improved LLM interactions
4. Leverage the existing HADES infrastructure including tiered storage hardware
5. Maintain backward compatibility with existing APIs and tools

## 2. Enhanced Path Retrieval with Flow-Based Pruning

The current path retrieval in HADES uses a simple hop-limited approach. We will enhance this with flow-based pruning as described in PathRAG.

### 2.1 Resource Allocation and Path Scoring

```python
def calculate_path_score(self, path, source_node, decay_rate=0.85):
    """
    Calculate the reliability score for a path using flow-based methods
    with distance awareness as described in PathRAG.
    
    Args:
        path: The path to score
        source_node: The starting node in the path
        decay_rate: Rate at which information decays along the path
    
    Returns:
        Normalized reliability score for the path
    """
    # Initialize the resource at the source node
    resource = {source_node: 1.0}
    path_score = 0.0
    
    # Process each edge in the path
    for i, edge in enumerate(path["edges"]):
        from_node = edge["_from"]
        to_node = edge["_to"]
        
        # Skip if the from_node has no resource
        if from_node not in resource:
            continue
        
        # Calculate resource flow with decay penalty
        flow = resource[from_node] * (decay_rate ** i)
        
        # Add to receiving node's resource
        resource[to_node] = resource.get(to_node, 0) + flow
        
        # Add to path score
        path_score += flow
    
    # Normalize by path length for fair comparison
    return path_score / len(path["edges"]) if path["edges"] else 0
```

### 2.2 Pruning Algorithm

```python
def prune_paths(self, candidate_paths, pruning_threshold=0.01):
    """
    Prune paths based on their resource flow scores.
    
    Args:
        candidate_paths: List of potential paths to consider
        pruning_threshold: Minimum score for a path to be retained
        
    Returns:
        List of pruned paths with their reliability scores
    """
    pruned_paths = []
    
    for path in candidate_paths:
        # Calculate resource flow-based score
        score = self.calculate_path_score(path, path["vertices"][0])
        
        # Only keep paths above the threshold
        if score >= pruning_threshold:
            path["reliability"] = score
            pruned_paths.append(path)
    
    # Sort by reliability score
    return sorted(pruned_paths, key=lambda p: p["reliability"], reverse=True)
```

### 2.3 Enhanced AQL Queries for Path Retrieval

The current simple path query:

```aql
FOR v, e, p IN 1..5 OUTBOUND 'entities/{query}' edges
    FILTER p.vertices[*].domain ALL == @domain_filter OR NOT @domain_filter
    LIMIT @max_paths
    RETURN {
        "path": CONCAT_SEPARATOR(' -> ', p.vertices[*].name),
        "vertices": p.vertices,
        "score": LENGTH(p.vertices)
    }
```

Will be enhanced to retrieve more metadata needed for intelligent pruning:

```aql
FOR v, e, p IN 1..7 OUTBOUND 'entities/{query}' edges
    FILTER p.vertices[*].domain ALL == @domain_filter OR NOT @domain_filter
    LET edge_weights = (
        FOR edge IN p.edges
        RETURN edge.weight || 1.0
    )
    LET edge_types = (
        FOR edge IN p.edges
        RETURN edge.type
    )
    RETURN {
        "path": CONCAT_SEPARATOR(' -> ', p.vertices[*].name),
        "vertices": p.vertices,
        "edges": p.edges,
        "edge_weights": edge_weights,
        "edge_types": edge_types,
        "vertex_types": p.vertices[*].type,
        "path_length": LENGTH(p.vertices)
    }
```

## 3. Tiered Memory Management System

Leveraging HADES' existing hardware infrastructure, we'll implement a tiered memory system inspired by MemGPT but adapted for our graph-based knowledge representation.

### 3.1 Memory Tiers Definition

```python
class MemoryTier(Enum):
    """Enumeration of memory tiers in order of access speed."""
    RAM = 1        # Fastest: RAM-based cache
    NVME_RAID0 = 2 # Fast: NVMe RAID0 storage
    RAID1 = 3      # Reliable: RAID1 storage
    RAID5 = 4      # Capacity: Primary ArangoDB on RAID5
```

### 3.2 Cache Implementation

```python
class LRUCache:
    """
    LRU (Least Recently Used) cache implementation for storing
    frequently accessed entities and paths in RAM.
    """
    def __init__(self, max_size_mb=8192):  # Default 8GB cache
        self.max_size_mb = max_size_mb
        self.current_size_mb = 0
        self.cache = OrderedDict()
        
    def get(self, key):
        """Retrieve an item from cache and update its position in LRU order."""
        if key not in self.cache:
            return None
        
        # Move to end (most recently used)
        value = self.cache.pop(key)
        self.cache[key] = value
        return value
        
    def put(self, key, value, size_mb=None):
        """Add an item to the cache, evicting items if necessary."""
        # Calculate item size if not provided
        if size_mb is None:
            size_mb = self._estimate_size_mb(value)
            
        # If item is too large for cache, don't cache it
        if size_mb > self.max_size_mb:
            return False
            
        # If item exists, remove it first
        if key in self.cache:
            old_size = self._estimate_size_mb(self.cache[key])
            self.current_size_mb -= old_size
            self.cache.pop(key)
            
        # Evict items until we have space
        while self.current_size_mb + size_mb > self.max_size_mb and self.cache:
            oldest_key, oldest_value = self.cache.popitem(last=False)
            self.current_size_mb -= self._estimate_size_mb(oldest_value)
            
        # Add the new item
        self.cache[key] = value
        self.current_size_mb += size_mb
        return True
        
    def _estimate_size_mb(self, obj):
        """Estimate the memory size of an object in MB."""
        # Simple estimation based on JSON serialization size
        # For production, use a more accurate approach like sys.getsizeof
        import json
        try:
            size_bytes = len(json.dumps(obj).encode('utf-8'))
            return size_bytes / (1024 * 1024)  # Convert to MB
        except:
            # Fallback for non-serializable objects
            return 0.1  # Assume 100KB
```

### 3.3 Disk Cache Implementation

```python
class DiskCache:
    """
    Persistent disk-based cache for entities and paths.
    Uses different storage tiers based on configured paths.
    """
    def __init__(self, base_path, max_size_gb=100):
        self.base_path = base_path
        self.max_size_gb = max_size_gb
        self.index_path = os.path.join(base_path, "index.json")
        self.data_path = os.path.join(base_path, "data")
        
        # Create directories if they don't exist
        os.makedirs(self.data_path, exist_ok=True)
        
        # Load index if it exists, otherwise initialize empty
        if os.path.exists(self.index_path):
            with open(self.index_path, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {
                "items": {},
                "total_size_mb": 0
            }
            self._save_index()
    
    def get(self, key):
        """Retrieve an item from disk cache."""
        if key not in self.index["items"]:
            return None
            
        item_info = self.index["items"][key]
        item_path = os.path.join(self.data_path, item_info["filename"])
        
        try:
            with open(item_path, 'r') as f:
                data = json.load(f)
                
            # Update access time
            item_info["last_accessed"] = time.time()
            item_info["access_count"] += 1
            self._save_index()
            
            return data
        except:
            # Handle corrupted data by removing it from index
            self.remove(key)
            return None
    
    def put(self, key, value, metadata=None):
        """Store an item in disk cache."""
        # Convert value to JSON and calculate size
        value_json = json.dumps(value)
        size_mb = len(value_json.encode('utf-8')) / (1024 * 1024)
        
        # Check if we need to make space
        if key not in self.index["items"] and self.index["total_size_mb"] + size_mb > self.max_size_gb * 1024:
            self._evict_items(size_mb)
        
        # Generate filename using key's hash
        filename = f"{hashlib.md5(key.encode()).hexdigest()}.json"
        item_path = os.path.join(self.data_path, filename)
        
        # Save data to file
        with open(item_path, 'w') as f:
            f.write(value_json)
        
        # Update index
        if key in self.index["items"]:
            old_size = self.index["items"][key]["size_mb"]
            self.index["total_size_mb"] -= old_size
        
        self.index["items"][key] = {
            "filename": filename,
            "size_mb": size_mb,
            "created": time.time(),
            "last_accessed": time.time(),
            "access_count": 1,
            "metadata": metadata or {}
        }
        
        self.index["total_size_mb"] += size_mb
        self._save_index()
        return True
    
    def remove(self, key):
        """Remove an item from disk cache."""
        if key not in self.index["items"]:
            return False
            
        item_info = self.index["items"][key]
        item_path = os.path.join(self.data_path, item_info["filename"])
        
        # Remove file if it exists
        if os.path.exists(item_path):
            os.remove(item_path)
        
        # Update index
        self.index["total_size_mb"] -= item_info["size_mb"]
        del self.index["items"][key]
        self._save_index()
        
        return True
    
    def _evict_items(self, required_space_mb):
        """Evict least recently used items to make space."""
        # Sort items by last access time, oldest first
        sorted_items = sorted(
            self.index["items"].items(),
            key=lambda x: (x[1]["last_accessed"], -x[1]["access_count"])
        )
        
        space_freed = 0
        for key, item in sorted_items:
            if space_freed >= required_space_mb:
                break
                
            self.remove(key)
            space_freed += item["size_mb"]
    
    def _save_index(self):
        """Save the index to disk."""
        with open(self.index_path, 'w') as f:
            json.dump(self.index, f)
```

### 3.4 Tiered Memory Manager

```python
class TieredMemoryManager:
    """
    Manages the movement of data between different memory tiers
    based on access patterns and importance.
    """
    def __init__(self, config=None):
        # Default configuration
        self.config = config or {
            "ram_cache_size_mb": 8192,  # 8GB RAM cache
            "nvme_cache_path": "/home/todd/.cache/hades_fast",
            "nvme_cache_size_gb": 200,
            "reliable_store_path": "/var/lib/hades_reliable",
            "reliable_store_size_gb": 500,
            "promotion_threshold": 5,  # Access count for promotion
            "importance_threshold": 0.7  # Importance score for higher tier
        }
        
        # Initialize caches
        self.ram_cache = LRUCache(max_size_mb=self.config["ram_cache_size_mb"])
        self.nvme_cache = DiskCache(self.config["nvme_cache_path"], self.config["nvme_cache_size_gb"])
        self.reliable_store = DiskCache(self.config["reliable_store_path"], self.config["reliable_store_size_gb"])
        
        # Reference to database (set during PathRAG initialization)
        self.db = None
    
    def get(self, key, context=None):
        """
        Retrieve data from the appropriate tier, starting with fastest.
        Updates access patterns and may trigger promotion.
        
        Args:
            key: Cache key to retrieve
            context: Optional context information for smart prefetching
            
        Returns:
            Retrieved data or None if not found
        """
        # Try RAM cache first (fastest)
        result = self.ram_cache.get(key)
        if result:
            return result
            
        # Try NVMe cache next
        result = self.nvme_cache.get(key)
        if result:
            # Consider promoting to RAM if accessed frequently
            item_info = self.nvme_cache.index["items"].get(key, {})
            if item_info.get("access_count", 0) >= self.config["promotion_threshold"]:
                self._promote_to_ram(key, result)
            return result
            
        # Try reliable store
        result = self.reliable_store.get(key)
        if result:
            # Consider promoting to NVMe if accessed frequently
            item_info = self.reliable_store.index["items"].get(key, {})
            if item_info.get("access_count", 0) >= self.config["promotion_threshold"]:
                self._promote_to_nvme(key, result)
            return result
            
        # Not in any cache, try database (slowest tier)
        if self.db:
            try:
                result = self._fetch_from_database(key)
                if result:
                    # Store in appropriate tier based on importance
                    importance = self._calculate_importance(result, context)
                    self._store_by_importance(key, result, importance)
                return result
            except Exception as e:
                logging.error(f"Error retrieving from database: {e}")
                
        return None
    
    def put(self, key, value, importance=None, context=None):
        """
        Store data in the appropriate tier based on importance.
        
        Args:
            key: Cache key
            value: Data to store
            importance: Optional predetermined importance score
            context: Optional context information
            
        Returns:
            Boolean indicating success
        """
        if importance is None:
            importance = self._calculate_importance(value, context)
            
        return self._store_by_importance(key, value, importance)
    
    def _calculate_importance(self, data, context=None):
        """
        Calculate the importance score of data to determine storage tier.
        Higher score = more important = faster tier.
        
        Args:
            data: The data to evaluate
            context: Optional context information
            
        Returns:
            Importance score between 0 and 1
        """
        # Default importance calculation
        # This would be enhanced with ML-based scoring in production
        base_score = 0.5  # Default medium importance
        
        modifiers = []
        
        # Add modifiers based on data properties
        if isinstance(data, dict):
            # Recently created/updated items are more important
            if "updated_at" in data:
                try:
                    updated_time = datetime.fromisoformat(data["updated_at"])
                    age_days = (datetime.utcnow() - updated_time).days
                    if age_days < 1:
                        modifiers.append(0.3)  # Very recent
                    elif age_days < 7:
                        modifiers.append(0.2)  # Recent
                    elif age_days < 30:
                        modifiers.append(0.1)  # Somewhat recent
                except:
                    pass
            
            # Confidence impacts importance
            if "confidence" in data:
                conf = float(data["confidence"])
                if conf > 0.8:
                    modifiers.append(0.2)
                elif conf > 0.5:
                    modifiers.append(0.1)
                    
            # Paths with more vertices/edges are often more valuable
            if "vertices" in data and isinstance(data["vertices"], list):
                if len(data["vertices"]) > 10:
                    modifiers.append(0.2)
                elif len(data["vertices"]) > 5:
                    modifiers.append(0.1)
                    
        # Consider context if provided
        if context and "recent_queries" in context:
            # Data relevant to recent queries is more important
            # Simple heuristic: check if any recent query appears in data
            data_str = str(data).lower()
            for query in context["recent_queries"]:
                if query.lower() in data_str:
                    modifiers.append(0.3)
                    break
        
        # Apply modifiers
        for mod in modifiers:
            base_score += mod
            
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, base_score))
    
    def _store_by_importance(self, key, value, importance):
        """Store data in the appropriate tier based on importance score."""
        if importance >= self.config["importance_threshold"]:
            # High importance - store in RAM
            return self.ram_cache.put(key, value)
        elif importance >= self.config["importance_threshold"] / 2:
            # Medium importance - store in NVMe
            return self.nvme_cache.put(key, value)
        else:
            # Lower importance - store in reliable storage
            return self.reliable_store.put(key, value)
    
    def _promote_to_ram(self, key, value):
        """Promote data from NVMe to RAM cache."""
        self.ram_cache.put(key, value)
        
    def _promote_to_nvme(self, key, value):
        """Promote data from reliable store to NVMe cache."""
        self.nvme_cache.put(key, value)
        
    def _fetch_from_database(self, key):
        """Fetch data from the database (slowest tier)."""
        # Implementation depends on what 'key' represents
        # For entity lookup by key:
        if key.startswith("entity:"):
            entity_key = key.split(":", 1)[1]
            # Use AQL to fetch entity
            aql = f"FOR doc IN entities FILTER doc._key == @key RETURN doc"
            result = self.db.execute_query(aql, {"key": entity_key})
            return result["result"][0] if result.get("result") else None
            
        # For path retrieval by query:
        elif key.startswith("path:"):
            query_parts = key.split(":", 2)
            if len(query_parts) >= 2:
                query = query_parts[1]
                params = json.loads(query_parts[2]) if len(query_parts) > 2 else {}
                
                # Logic for path retrieval
                from_entity = params.get("from", query)
                aql = f"""
                FOR v, e, p IN 1..7 OUTBOUND 'entities/{from_entity}' edges
                    FILTER p.vertices[*].domain ALL == @domain_filter OR NOT @domain_filter
                    LIMIT @max_paths
                    RETURN {{
                        "path": CONCAT_SEPARATOR(' -> ', p.vertices[*].name),
                        "vertices": p.vertices,
                        "edges": p.edges
                    }}
                """
                
                domain_filter = params.get("domain_filter")
                max_paths = params.get("max_paths", 5)
                
                result = self.db.execute_query(aql, {
                    "domain_filter": domain_filter,
                    "max_paths": max_paths
                })
                
                return {"paths": result.get("result", [])} if result.get("success") else None
        
        return None
```
## 4. Context Window Management

Inspired by MemGPT's approach to handling extended context windows, we'll implement a context window manager that optimizes the use of limited LLM context space.

### 4.1 Context Window Manager

```python
class ContextWindowManager:
    """
    Manages the LLM context window by optimizing the content to fit
    within token limits while preserving the most relevant information.
    Inspired by MemGPT's context management techniques.
    """
    def __init__(self, max_tokens=4096, reserve_tokens=512):
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens  # Reserved for prompt and response
        self.available_tokens = max_tokens - reserve_tokens
        
        # Track token usage
        self.current_token_count = 0
        
        # Context sections ordered by priority
        self.context = {
            "high_priority": [],   # Critical paths, recent context
            "medium_priority": [], # Supporting paths, domain knowledge
            "low_priority": []     # Background knowledge, fallback info
        }
        
        # Token counting function - in production, use a proper tokenizer
        self.count_tokens = lambda text: len(text.split()) // 3
    
    def add_path(self, path, priority="medium_priority"):
        """
        Add a path to the context window with specified priority.
        
        Args:
            path: Path data to add
            priority: Priority level (high, medium, low)
            
        Returns:
            Boolean indicating if path was added successfully
        """
        if priority not in self.context:
            priority = "medium_priority"
            
        # Convert path to text representation
        path_text = self._path_to_text(path)
        token_count = self.count_tokens(path_text)
        
        # Check if adding this would exceed our limit
        if self.current_token_count + token_count > self.available_tokens:
            # Need to make space
            self._make_space(token_count)
            
        # If we still don't have space, the path is too large or
        # we couldn't free enough space
        if self.current_token_count + token_count > self.available_tokens:
            return False
            
        # Add the path with its metadata
        self.context[priority].append({
            "text": path_text,
            "tokens": token_count,
            "metadata": path.get("metadata", {}),
            "reliability": path.get("reliability", 0.5)
        })
        
        self.current_token_count += token_count
        return True
    
    def _make_space(self, required_tokens):
        """
        Make space in the context window by removing lower priority content.
        Uses a strategy inspired by MemGPT's page eviction.
        """
        # First try to remove low priority items
        space_freed = self._evict_from_priority("low_priority", required_tokens)
        if space_freed >= required_tokens:
            return True
            
        # If still need space, try medium priority
        space_freed += self._evict_from_priority("medium_priority", required_tokens - space_freed)
        if space_freed >= required_tokens:
            return True
            
        # As a last resort, remove from high priority
        space_freed += self._evict_from_priority("high_priority", required_tokens - space_freed)
        return space_freed >= required_tokens
    
    def _evict_from_priority(self, priority, required_tokens):
        """Evict items from a specific priority level."""
        if not self.context[priority]:
            return 0
            
        # Sort by reliability (ascending) so we remove least reliable first
        self.context[priority].sort(key=lambda x: x.get("reliability", 0))
        
        tokens_freed = 0
        items_to_remove = []
        
        for i, item in enumerate(self.context[priority]):
            tokens_freed += item["tokens"]
            items_to_remove.append(i)
            
            if tokens_freed >= required_tokens:
                break
        
        # Remove the identified items (in reverse order to avoid index issues)
        for idx in sorted(items_to_remove, reverse=True):
            self.current_token_count -= self.context[priority][idx]["tokens"]
            self.context[priority].pop(idx)
            
        return tokens_freed
    
    def _path_to_text(self, path):
        """Convert a path object to its text representation."""
        if "text" in path:
            return path["text"]
            
        # If we need to generate text from path components
        text = path.get("path", "")
        
        # Add additional context from vertices/edges if available
        if "vertices" in path and isinstance(path["vertices"], list):
            for vertex in path["vertices"]:
                if "description" in vertex and vertex["description"]:
                    text += f"\n- {vertex.get('name', 'Entity')}: {vertex['description']}"
        
        return text
    
    def get_formatted_context(self):
        """
        Get the formatted context for inclusion in LLM prompts.
        Follows MemGPT's golden memory region principle by placing
        high priority content at the beginning and end of the context.
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
        
    def summarize_context(self, model_processor=None):
        """
        Create a summarized version of the context to save tokens.
        Uses embedded LLM if available, otherwise uses heuristics.
        """
        if model_processor and hasattr(model_processor, 'summarize'):
            # Use LLM to summarize content
            full_context = self.get_formatted_context()
            return model_processor.summarize(full_context)
        
        # Simple heuristic summarization as fallback
        summary_parts = []
        
        # Summarize high priority fully
        high_priority_text = "\n".join([item["text"] for item in self.context["high_priority"]])
        summary_parts.append(high_priority_text)
        
        # Summarize medium priority (take first sentence of each item)
        for item in self.context["medium_priority"]:
            first_sentence = item["text"].split('.')[0] + '.'
            summary_parts.append(first_sentence)
            
        # Just mention low priority exists if any
        if self.context["low_priority"]:
            count = len(self.context["low_priority"])
            summary_parts.append(f"Additional {count} background context items available.")
            
        return "\n\n".join(summary_parts)
```

### 4.2 Path Ordering for LLM Prompts

Based on PathRAG's insights about the "lost in the middle" phenomenon, we'll implement a strategic path ordering function:

```python
def format_paths_for_prompt(self, paths, query):
    """
    Order paths by reliability for optimal LLM consumption.
    Addresses the "lost in the middle" issue identified in PathRAG.
    
    Args:
        paths: List of path objects with reliability scores
        query: Original user query
        
    Returns:
        Formatted prompt text with paths in strategic order
    """
    # First ensure all paths have reliability scores
    for path in paths:
        if "reliability" not in path:
            path["reliability"] = self.calculate_path_score(path, path["vertices"][0])
    
    # Sort paths by reliability (ascending)
    sorted_paths = sorted(paths, key=lambda p: p["reliability"])
    
    # Format prompt with query at the beginning and most reliable path at the end
    prompt = f"Query: {query}\n\nRelevant information:\n\n"
    
    # Add medium reliability paths first (middle of the prompt)
    middle_paths = sorted_paths[:-1] if len(sorted_paths) > 1 else []
    for path in middle_paths:
        # Format the path text
        path_text = f"Path ({path['reliability']:.2f}): {path['path']}\n"
        if "vertices" in path and isinstance(path["vertices"], list):
            for vertex in path["vertices"]:
                if "description" in vertex and vertex["description"]:
                    path_text += f"  - {vertex.get('name', 'Entity')}: {vertex['description']}\n"
        prompt += path_text + "\n"
    
    # Add the most reliable path last (end of the prompt - golden memory region)
    if sorted_paths:
        most_reliable = sorted_paths[-1]
        prompt += f"Most relevant path ({most_reliable['reliability']:.2f}): {most_reliable['path']}\n"
        if "vertices" in most_reliable and isinstance(most_reliable["vertices"], list):
            for vertex in most_reliable["vertices"]:
                if "description" in vertex and vertex["description"]:
                    prompt += f"  - {vertex.get('name', 'Entity')}: {vertex['description']}\n"
    
    return prompt
```

## 5. Integration with Existing PathRAG Implementation

To maintain backward compatibility while enhancing the system, we'll implement a `MemoryEnhancedPathRAG` class that extends the existing `PathRAG` implementation.

### 5.1 Enhanced PathRAG Class

```python
class MemoryEnhancedPathRAG(PathRAG):
    """
    Enhancement of the base PathRAG with memory management
    and improved path retrieval algorithms.
    
    This implementation integrates concepts from both PathRAG and MemGPT papers
    while maintaining compatibility with the existing HADES infrastructure.
    """
    
    def __init__(self, config=None):
        """Initialize the memory-enhanced PathRAG module."""
        super().__init__()
        
        # Default configuration
        self.config = config or {
            "decay_rate": 0.85,
            "pruning_threshold": 0.01,
            "max_cache_paths": 100,
            "path_token_estimate": 150,
            "context_window_tokens": 4096,
            "reserve_tokens": 512,
            "enable_caching": True,
            "ram_cache_size_mb": 8192,
            "nvme_cache_path": "/home/todd/.cache/hades_pathrag",
            "nvme_cache_size_gb": 50,
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
        self.recent_queries = deque(maxlen=10)
        
        logger.info("Initialized Memory-Enhanced PathRAG module")
    
    def retrieve_paths(self, query, max_paths=5, domain_filter=None, as_of_version=None):
        """
        Enhanced path retrieval with caching and flow-based pruning.
        Maintains the same API as the original implementation.
        
        Args:
            query: The query to retrieve paths for
            max_paths: Maximum number of paths to retrieve
            domain_filter: Optional domain filter
            as_of_version: Optional version to query against
            
        Returns:
            Dict containing the retrieved paths with metadata
        """
        logger.info(f"Memory-Enhanced PathRAG retrieving paths for query: {query}")
        
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
                logger.info(f"Cache hit for query: {query}")
                return cached_result
        
        # Cache miss, perform database query
        try:
            # Execute the base retrieval to get candidate paths
            base_result = super().retrieve_paths(query, max_paths * 2, domain_filter, as_of_version)
            
            if not base_result.get("success", False):
                return base_result
                
            # Apply flow-based pruning to the retrieved paths
            raw_paths = base_result.get("paths", [])
            
            # Enhanced processing
            if raw_paths:
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
            else:
                result = base_result
                
            # Cache the result
            if self.config["enable_caching"] and hasattr(self, 'memory_manager'):
                context = {"recent_queries": list(self.recent_queries)}
                importance = 0.7 if len(pruned_paths) > 0 else 0.3  # More paths = more important
                self.memory_manager.put(cache_key, result, importance, context)
                
            return result
                
        except Exception as e:
            logger.error(f"Enhanced path retrieval failed: {e}")
            return {
                "success": False,
                "error": f"Enhanced path retrieval failed: {str(e)}"
            }
    
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
        
    def format_paths_for_prompt(self, paths, query):
        """Format retrieved paths for optimal LLM consumption."""
        # Use the strategic path ordering function
        return format_paths_for_prompt(self, paths, query)
        
    def retrieve_and_format(self, query, max_paths=5, domain_filter=None, as_of_version=None):
        """
        Retrieve paths and format them for LLM prompting in one step.
        
        Args:
            query: The query to retrieve paths for
            max_paths: Maximum number of paths to retrieve
            domain_filter: Optional domain filter
            as_of_version: Optional version to query against
            
        Returns:
            Formatted prompt text ready for LLM consumption
        """
        # Retrieve paths
        result = self.retrieve_paths(query, max_paths, domain_filter, as_of_version)
        
        if not result.get("success", False):
            return f"Error retrieving paths: {result.get('error', 'Unknown error')}"
            
        paths = result.get("paths", [])
        if not paths:
            return f"No paths found for query: {query}"
            
        # Format paths for prompt
        return self.format_paths_for_prompt(paths, query)
```

### 5.2 MCP Server Integration

The existing MCP server tools can be enhanced to use the memory-enhanced PathRAG:

```python
async def pathrag_retrieve(self, params: Dict[str, Any], session_data: Dict[str, Any]):
    """
    Enhanced tool handler to retrieve paths using Memory-Enhanced PathRAG.
    Maintains the same API as the original implementation.
    
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
    logger.info(f"Executing memory-enhanced pathrag_retrieve tool")
    
    # Check authentication (same as original)
    if not session_data.get("authenticated", False):
        return {
            "success": False,
            "error": "Not authenticated"
        }
    
    # Extract parameters (same as original)
    query = params.get("query", "")
    max_paths = params.get("max_paths", 5)
    domain_filter = params.get("domain_filter")
    as_of_version = params.get("as_of_version")
    format_for_llm = params.get("format_for_llm", False)
    
    # Validate parameters (same as original)
    if not query:
        return {
            "success": False,
            "error": "Query is required"
        }
    
    try:
        # Initialize Memory-Enhanced PathRAG
        from src.rag.memory_enhanced_path_rag import MemoryEnhancedPathRAG
        
        # Create a fresh instance for this request
        fresh_path_rag = MemoryEnhancedPathRAG()
        
        # Call the appropriate method based on format_for_llm flag
        if format_for_llm:
            result = fresh_path_rag.retrieve_and_format(
                query=query,
                max_paths=max_paths,
                domain_filter=domain_filter,
                as_of_version=as_of_version
            )
            # Return as string if formatted for LLM
            return {
                "success": True,
                "formatted_prompt": result
            }
        else:
            # Standard path retrieval
            result = fresh_path_rag.retrieve_paths(
                query=query,
                max_paths=max_paths,
                domain_filter=domain_filter,
                as_of_version=as_of_version
            )
            
            logger.info(f"Memory-enhanced PathRAG retrieve result: {result}")
            return result
            
    except Exception as e:
        logger.error(f"Error retrieving paths with memory-enhanced PathRAG: {e}")
        return {
            "success": False,
            "error": f"Error retrieving paths: {str(e)}"
        }
```

## 6. Implementation Plan

### 6.1 Phase 1: Core PathRAG Enhancements

1. **Flow-Based Path Scoring (Week 1)**
   - Implement `calculate_path_score` with resource flow algorithm
   - Update AQL queries to retrieve edge weights and types
   - Create path pruning logic with configurable thresholds

2. **Path Formatting for LLM (Week 1)**
   - Implement optimal path ordering for prompts
   - Address "lost in the middle" issue with strategic placement
   - Create robust text conversion for paths with metadata

### 6.2 Phase 2: Memory Management Integration (Week 2)

1. **Tiered Memory System**
   - Implement `LRUCache` for RAM-based caching
   - Create `DiskCache` for NVMe and reliable storage
   - Develop `TieredMemoryManager` to coordinate between tiers

2. **Context Window Manager**
   - Implement token counting and budget management
   - Create dynamic context assembly with prioritization
   - Add summarization capabilities for context reduction

### 6.3 Phase 3: Integration with Existing System (Week 3)

1. **MemoryEnhancedPathRAG Class**
   - Create extension of existing PathRAG
   - Ensure backward compatibility with current code
   - Implement unified retrieve_and_format method

2. **MCP Tool Updates**
   - Enhance existing MCP server tools to use new features
   - Add format_for_llm parameter for direct prompt generation
   - Maintain compatibility with current API

### 6.4 Phase 4: Testing and Optimization (Week 4)

1. **Performance Testing**
   - Benchmark retrieval speeds with/without caching
   - Test memory usage across different loads
   - Optimize configuration parameters

2. **Quality Evaluation**
   - Compare path quality with old vs. new algorithms
   - Evaluate prompt quality for LLM consumption
   - Fine-tune reliability calculation and pruning thresholds

## 7. Conclusion

This enhancement plan combines the strengths of PathRAG's flow-based pruning algorithms with MemGPT's tiered memory management approach. By integrating these research-backed techniques into HADES' existing architecture, we can significantly improve both the quality of retrieved paths and the system's overall performance.

The implementation maintains backward compatibility while adding powerful new capabilities:

1. More relevant path retrieval through flow-based scoring
2. Efficient memory utilization through tiered storage
3. Optimized context window management for LLM interactions
4. Strategic prompt formatting for improved LLM responses

These enhancements leverage HADES' existing hardware infrastructure while introducing software optimizations that follow state-of-the-art research in graph-based RAG systems and memory management.

## 8. References

1. Wu, X., Zhang, Y., Feng, Y., Wang, D., Wang, H., Lai, C., Fang, M., Chen, R., Lim, E., Su, J., Zheng, N., & Chua, T. (2024). "PathRAG: Pruning Graph-based Retrieval Augmented Generation with Relational Paths." arXiv:2502.14902.

2. Packer, C., Wooders, S., Lin, K., Fang, V., Patil, S. G., Stoica, I., & Gonzalez, J. E. (2023). "MemGPT: Towards LLMs as Operating Systems." arXiv:2310.08560.

3. Lü, L., & Zhou, T. (2011). "Link prediction in complex networks: A survey." Physica A: Statistical Mechanics and Its Applications, 390(6), 1150-1170.

4. Liu, N., Zhang, Z., Yu, W., Wang, H., Cheng, H., Zhuang, Y., Cheng, Y., Lin, L., Lu, S., & Chen, X. (2024). "Lost in the Middle: How Language Models Use Long Contexts."
