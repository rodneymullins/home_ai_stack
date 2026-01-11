"""
Mem0 Memory Client

Unified interface for Mem0 memory operations across the Fellowship stack.
Uses your existing Mem0 config (pgvector + Neo4j + Ollama).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import sys
import os

# Ensure we can import from src/core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@dataclass
class MemoryResult:
    """A memory result from Mem0."""
    id: str
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = None


class MemoryClient:
    """
    Client for Mem0 memory operations.
    
    Usage:
        client = MemoryClient()
        client.add("User prefers concise responses", user_id="rod")
        results = client.search("user preferences", user_id="rod")
    """
    
    def __init__(self):
        self._memory = None
    
    @property
    def memory(self):
        """Lazy-load Mem0 instance."""
        if self._memory is None:
            from src.core.mem0_config import create_memory
            self._memory = create_memory()
        return self._memory
    
    def add(self, text: str, user_id: str = "default", metadata: Dict = None) -> bool:
        """
        Add a memory.
        
        Args:
            text: The memory content
            user_id: User ID for memory isolation
            metadata: Optional metadata dict
        """
        try:
            self.memory.add(text, user_id=user_id, metadata=metadata or {})
            return True
        except Exception as e:
            print(f"[MEM0] Failed to add memory: {e}")
            return False
    
    def search(self, query: str, user_id: str = "default", limit: int = 5) -> List[MemoryResult]:
        """
        Search memories.
        
        Args:
            query: Search query
            user_id: User ID to search within
            limit: Max results
        """
        try:
            results = self.memory.search(query, user_id=user_id, limit=limit)
            return [
                MemoryResult(
                    id=r.get("id", ""),
                    text=r.get("memory", r.get("text", "")),
                    metadata=r.get("metadata", {}),
                    score=r.get("score")
                )
                for r in results.get("results", results) if isinstance(results, dict) else results
            ]
        except Exception as e:
            print(f"[MEM0] Search failed: {e}")
            return []
    
    def get_all(self, user_id: str = "default") -> List[MemoryResult]:
        """Get all memories for a user."""
        try:
            results = self.memory.get_all(user_id=user_id)
            return [
                MemoryResult(
                    id=r.get("id", ""),
                    text=r.get("memory", r.get("text", "")),
                    metadata=r.get("metadata", {})
                )
                for r in results.get("results", results) if isinstance(results, dict) else results
            ]
        except Exception as e:
            print(f"[MEM0] Get all failed: {e}")
            return []
    
    # === Convenience Methods ===
    
    def add_trade(self, symbol: str, action: str, reasoning: str, user_id: str = "kalshi_bot") -> bool:
        """Add a trade memory."""
        text = f"Trade {action} on {symbol}: {reasoning}"
        return self.add(text, user_id=user_id, metadata={
            "type": "trade", "symbol": symbol, "action": action
        })
    
    def add_preference(self, preference: str, user_id: str = "rod", category: str = "general") -> bool:
        """Add a user preference."""
        return self.add(f"User preference: {preference}", user_id=user_id, metadata={
            "type": "preference", "category": category
        })
    
    def add_insight(self, insight: str, source: str = "dashboard", user_id: str = "system") -> bool:
        """Add a system insight."""
        return self.add(f"Insight: {insight}", user_id=user_id, metadata={
            "type": "insight", "source": source
        })
    
    def get_context(self, query: str, user_id: str = "default", max_tokens: int = 500) -> str:
        """Get formatted context for RAG injection."""
        memories = self.search(query, user_id=user_id, limit=5)
        if not memories:
            return ""
        
        lines = ["[Relevant Memory Context]"]
        chars = 0
        for m in memories:
            if chars + len(m.text) > max_tokens * 4:
                break
            lines.append(f"• {m.text}")
            chars += len(m.text)
        
        return "\n".join(lines)


# Singleton
_client = None

def get_memory_client() -> MemoryClient:
    global _client
    if _client is None:
        _client = MemoryClient()
    return _client

# Quick access
def add_memory(text: str, user_id: str = "default") -> bool:
    return get_memory_client().add(text, user_id)

def search_memory(query: str, user_id: str = "default", limit: int = 5) -> List[MemoryResult]:
    return get_memory_client().search(query, user_id, limit)

def get_context(query: str, user_id: str = "default") -> str:
    return get_memory_client().get_context(query, user_id)


if __name__ == "__main__":
    print("=== Mem0 Memory Client Test ===")
    client = MemoryClient()
    
    # Test add
    print("Adding test memory...")
    success = client.add("Test memory from Mem0 client", user_id="test")
    print(f"Add: {'✓' if success else '✗'}")
    
    # Test search
    print("\nSearching...")
    results = client.search("test", user_id="test", limit=3)
    print(f"Found {len(results)} results")
    for r in results:
        print(f"  - {r.text[:50]}...")
