"""Official Mem0 configuration for Thor."""
import os
import sys
from mem0 import Memory

# Import centralized config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import GANDALF_IP, OLLAMA_HOST

def create_memory() -> Memory:
    """Create configured Memory instance using Ollama + Neo4j."""
    config = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "llama3.1:8b",
                "ollama_base_url": OLLAMA_HOST,
                "temperature": 0.1
            }
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text:latest",
                "ollama_base_url": OLLAMA_HOST
            }
        },
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "dbname": "postgres",
                "user": "postgres",
                "password": "homeai2025",
                "host": GANDALF_IP,
                "port": 5432,
                "collection_name": "memories"
            }
        },
        "graph_store": {
            "provider": "neo4j",
            "config": {
                "url": f"bolt://{GANDALF_IP}:7687",
                "username": "neo4j",
                "password": os.getenv("NEO4J_PASSWORD", "homeai2025"),
                "encrypted": False
            }
        },
        "version": "v1.1"
    }
    
    return Memory.from_config(config)
