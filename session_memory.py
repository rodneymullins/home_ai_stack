"""
Session Memory Manager (Mem0 Backend)

Stores user preferences, interactions, and patterns across sessions.
"""

from typing import List
from memory_client import get_memory_client, MemoryResult

class SessionMemory:
    """
    Cross-session memory manager using Mem0.
    
    Usage:
        session = SessionMemory(user_id="rod")
        session.remember_preference("prefers dark mode")
        context = session.get_session_context()
    """
    
    def __init__(self, user_id: str = "rod"):
        self.client = get_memory_client()
        self.user_id = user_id
    
    def remember_preference(self, preference: str, category: str = "general") -> bool:
        """Store a user preference."""
        return self.client.add_preference(preference, user_id=self.user_id, category=category)
    
    def remember_interaction(self, summary: str) -> bool:
        """Store a notable interaction."""
        return self.client.add(
            f"Notable session: {summary}",
            user_id=self.user_id,
            metadata={"type": "interaction"}
        )
    
    def remember_pattern(self, pattern: str, domain: str = "behavior") -> bool:
        """Store a learned pattern."""
        return self.client.add(
            f"Learned pattern: {pattern}",
            user_id=self.user_id,
            metadata={"type": "pattern", "domain": domain}
        )
    
    def get_preferences(self, limit: int = 10) -> List[MemoryResult]:
        """Get user preferences."""
        return self.client.search("user preference", user_id=self.user_id, limit=limit)
    
    def get_session_context(self) -> str:
        """Get formatted context for session initialization."""
        memories = self.client.search("preference OR pattern OR session", 
                                       user_id=self.user_id, limit=10)
        if not memories:
            return ""
        
        lines = [f"## Session Context for {self.user_id}:"]
        for m in memories[:10]:
            lines.append(f"• {m.text}")
        
        return "\n".join(lines)


# Convenience
_sessions = {}

def get_session(user_id: str = "rod") -> SessionMemory:
    if user_id not in _sessions:
        _sessions[user_id] = SessionMemory(user_id)
    return _sessions[user_id]


if __name__ == "__main__":
    print("=== Session Memory Test (Mem0) ===")
    session = SessionMemory(user_id="rod")
    
    # Add test data
    session.remember_preference("prefers concise responses", "communication")
    session.remember_pattern("works on Fellowship infrastructure late nights", "schedule")
    
    # Get context
    context = session.get_session_context()
    print(f"Context:\n{context}")
