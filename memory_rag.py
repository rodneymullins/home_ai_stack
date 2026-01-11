"""
Memory-Augmented RAG Pipeline (Mem0 Backend)

Injects relevant memories into prompts before LLM calls.
"""

from typing import Dict, Any
from memory_client import get_memory_client, MemoryResult

class MemoryRAG:
    """
    Memory-augmented prompt builder using Mem0.
    
    Usage:
        rag = MemoryRAG(user_id="rod")
        enhanced = rag.augment_prompt("What patterns in my trading?")
        # enhanced["user"] now contains memory context
    """
    
    def __init__(self, user_id: str = "default", max_context_tokens: int = 500):
        self.client = get_memory_client()
        self.user_id = user_id
        self.max_context_tokens = max_context_tokens
    
    def get_relevant_context(self, query: str, limit: int = 5) -> str:
        """Fetch relevant memories as formatted context."""
        memories = self.client.search(query, user_id=self.user_id, limit=limit)
        if not memories:
            return ""
        
        lines = ["[Relevant Memory Context]"]
        chars = 0
        max_chars = self.max_context_tokens * 4
        
        for mem in memories:
            line = f"• {mem.text}"
            if chars + len(line) > max_chars:
                break
            lines.append(line)
            chars += len(line)
        
        return "\n".join(lines)
    
    def augment_prompt(self, user_query: str, system_prompt: str = "", 
                       inject_position: str = "system") -> Dict[str, str]:
        """
        Augment a prompt with memory context.
        
        Args:
            user_query: The user's query
            system_prompt: Optional system prompt
            inject_position: "system" (recommended) or "user"
        """
        context = self.get_relevant_context(user_query)
        
        if not context:
            return {"system": system_prompt, "user": user_query}
        
        if inject_position == "system":
            return {
                "system": f"{system_prompt}\n\n{context}" if system_prompt else context,
                "user": user_query
            }
        else:
            return {
                "system": system_prompt,
                "user": f"{context}\n\n{user_query}"
            }
    
    def augment_for_ollama(self, user_query: str, model: str = "llama3.1:8b") -> Dict[str, Any]:
        """Create Ollama-ready request with memory context."""
        augmented = self.augment_prompt(user_query, inject_position="user")
        return {"model": model, "prompt": augmented["user"], "stream": False}


# Convenience
def augment_query(query: str, user_id: str = "rod", system: str = "") -> Dict[str, str]:
    """Quick augment a query with memory context."""
    return MemoryRAG(user_id=user_id).augment_prompt(query, system)


if __name__ == "__main__":
    print("=== Memory RAG Test (Mem0) ===")
    rag = MemoryRAG(user_id="rod")
    context = rag.get_relevant_context("test")
    print(f"Context:\n{context}")
