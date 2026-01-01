
import os

# --- Configuration Constants ---

# Milvus Connection
MILVUS_URI = os.getenv("MILVUS_URI", "./milvus_home_ai.db")

# OpenAI Compatible API (Exo / Ollama)
# Exo usually runs on port 8000 or 52000, Ollama on 11434. 
# We'll default to localhost:8000 for Exo based on valid history.
LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:8000/v1") 
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "openai/gpt-oss-20b") # Adjust based on what you have loaded in Exo/Ollama

MEM0_CONFIG = {
    "vector_store": {
        "provider": "milvus",
        "config": {
            "collection_name": "home_ai_memory",
            "embedding_model_dims": 768,
            "url": MILVUS_URI,
            "token": ""  # Empty for Milvus Lite (no auth)
        }
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": LLM_MODEL_NAME,  # Exo model name
            "temperature": 0.1,
            "max_tokens": 1500,
            "api_key": "dummy",  # Exo doesn't need a real key
            "openai_base_url": LLM_API_BASE  # Points to Exo
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": "http://localhost:11434" 
        }
    }
}
