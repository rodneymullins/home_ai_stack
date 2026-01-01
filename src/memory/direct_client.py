"""
Direct Milvus client for vector operations.
Bypasses Mem0 to avoid config issues.
"""

from pymilvus import MilvusClient, DataType
import ollama
import json
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DirectMemoryClient:
    """Simple memory client using Milvus directly."""
    
    def __init__(self, milvus_uri: str = "./milvus_home_ai.db", 
                 collection_name: str = "memories",
                 embedding_model: str = "nomic-embed-text"):
        self.milvus_uri = milvus_uri
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.client = None
        self.dim = 768  # nomic-embed-text dimension
        
    def connect(self):
        """Initialize Milvus connection and create collection if needed."""
        self.client = MilvusClient(uri=self.milvus_uri)
        
        # Create collection if it doesn't exist
        if not self.client.has_collection(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=self.dim,
                metric_type="COSINE",
                auto_id=True
            )
            logger.info(f"Created collection: {self.collection_name}")
        else:
            logger.info(f"Using existing collection: {self.collection_name}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama."""
        response = ollama.embed(model=self.embedding_model, input=text)
        return response['embeddings'][0]
    
    def save(self, content: str, user_id: str = "user", metadata: Dict[str, Any] = None) -> str:
        """Save content to vector store."""
        if not self.client:
            self.connect()
        
        # Get embedding
        embedding = self._get_embedding(content)
        
        # Prepare data
        data = {
            "vector": embedding,
            "content": content,
            "user_id": user_id,
            "metadata": json.dumps(metadata or {})
        }
        
        # Insert
        result = self.client.insert(
            collection_name=self.collection_name,
            data=[data]
        )
        
        return f"Saved with ID: {result['ids'][0]}"
    
    def search(self, query: str, user_id: str = "user", limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar content."""
        if not self.client:
            self.connect()
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_embedding],
            limit=limit,
            filter=f'user_id == "{user_id}"',
            output_fields=["content", "user_id", "metadata"]
        )
        
        # Format results
        memories = []
        for hits in results:
            for hit in hits:
                memories.append({
                    "id": hit['id'],
                    "content": hit['entity']['content'],
                    "score": hit['distance'],
                    "metadata": json.loads(hit['entity'].get('metadata', '{}'))
                })
        
        return memories
    
    def get_all(self, user_id: str = "user") -> List[Dict[str, Any]]:
        """Get all memories for a user."""
        if not self.client:
            self.connect()
        
        # Query all for user
        results = self.client.query(
            collection_name=self.collection_name,
            filter=f'user_id == "{user_id}"',
            output_fields=["content", "metadata"]
        )
        
        return [
            {
                "id": r['id'],
                "content": r['content'],
                "metadata": json.loads(r.get('metadata', '{}'))
            }
            for r in results
        ]
