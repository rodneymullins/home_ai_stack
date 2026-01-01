"""
Simple graph memory using NetworkX.
Tracks relationships between concepts and entities.
"""

import networkx as nx
import json
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class GraphMemory:
    """In-memory graph for tracking relationships."""
    
    def __init__(self, persist_path: str = "./graph_memory.json"):
        self.graph = nx.DiGraph()
        self.persist_path = persist_path
        self.load()
    
    def add_node(self, node_id: str, node_type: str, attributes: Dict[str, Any] = None):
        """Add a node to the graph."""
        self.graph.add_node(
            node_id,
            node_type=node_type,
            **(attributes or {})
        )
        logger.info(f"Added node: {node_id} ({node_type})")
    
    def add_edge(self, from_node: str, to_node: str, relationship: str, attributes: Dict[str, Any] = None):
        """Add an edge between nodes."""
        self.graph.add_edge(
            from_node,
            to_node,
            relationship=relationship,
            **(attributes or {})
        )
        logger.info(f"Added edge: {from_node} --[{relationship}]--> {to_node}")
    
    def get_neighbors(self, node_id: str) -> List[Tuple[str, str]]:
        """Get all neighbors and their relationships."""
        if node_id not in self.graph:
            return []
        
        neighbors = []
        for neighbor in self.graph.neighbors(node_id):
            relationship = self.graph[node_id][neighbor].get('relationship', 'related_to')
            neighbors.append((neighbor, relationship))
        
        return neighbors
    
    def get_paths(self, from_node: str, to_node: str, max_length: int = 3) -> List[List[str]]:
        """Find paths between two nodes."""
        if from_node not in self.graph or to_node not in self.graph:
            return []
        
        try:
            paths = list(nx.all_simple_paths(
                self.graph,
                from_node,
                to_node,
                cutoff=max_length
            ))
            return paths
        except nx.NetworkXNoPath:
            return []
    
    def save(self):
        """Persist graph to disk."""
        data = nx.node_link_data(self.graph)
        with open(self.persist_path, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Graph saved to {self.persist_path}")
    
    def load(self):
        """Load graph from disk."""
        try:
            with open(self.persist_path, 'r') as f:
                data = json.load(f)
            self.graph = nx.node_link_graph(data, directed=True)
            logger.info(f"Graph loaded from {self.persist_path}")
        except FileNotFoundError:
            logger.info("No existing graph found, starting fresh")
    
    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph)
        }
