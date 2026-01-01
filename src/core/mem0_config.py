"""Official Mem0 configuration for Thor."""
import os
from mem0 import Memory

def create_memory() -> Memory:
    """Create configured Memory instance using Ollama + Neo4j."""
    config = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "llama3.1:8b",
                "ollama_base_url": "http://192.168.1.211:11434",
                "temperature": 0.1
            }
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text:latest",
                "ollama_base_url": "http://192.168.1.211:11434"
            }
        },
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "dbname": "postgres",
                "user": "postgres",
                "password": "homeai2025",
                "host": "192.168.1.211",
                "port": 5432,
                "collection_name": "memories"
            }
        },
        "graph_store": {
            "provider": "neo4j",
            "config": {
                "url": "bolt://192.168.1.211:7687",
                "username": "neo4j",
                "password": os.getenv("NEO4J_PASSWORD", "homeai2025"),
                "encrypted": False
            }
        },
        "version": "v1.1"
    }
    
    return Memory.from_config(config)
