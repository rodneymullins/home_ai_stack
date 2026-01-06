#!/usr/bin/env python3
"""
The Fellowship AIRouter
Intelligent routing and failover for Ollama endpoints across The Fellowship.
"""

import requests
import time
from typing import Optional, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FellowshipRouter:
    """Routes AI requests with intelligent failover between Aragorn and Gandalf."""
    
    def __init__(self):
        self.endpoints = {
            'aragorn': {
                'url': 'http://192.168.1.18:11434',
                'priority': 1,
                'name': 'Aragorn (AI King)',
                'models': []  # Will be populated on health check
            },
            'gandalf': {
                'url': 'http://192.168.1.211:11434',
                'priority': 2,
                'name': 'Gandalf (Data Keeper)',
                'models': []
            }
        }
        self.timeout = 5
        self.retry_delay = 2
        
        # Load Balancing State
        self.strategy = 'round_robin'  # Options: 'priority', 'round_robin'
        self.current_index = 0
        
    def check_health(self, endpoint_name: str) -> bool:
        """Check if an endpoint is healthy and responsive."""
        endpoint = self.endpoints[endpoint_name]
        try:
            response = requests.get(
                f"{endpoint['url']}/api/tags",
                timeout=self.timeout
            )
            if response.status_code == 200:
                # Update available models
                data = response.json()
                endpoint['models'] = [m['name'] for m in data.get('models', [])]
                logger.info(f"✅ {endpoint['name']} is healthy ({len(endpoint['models'])} models)")
                return True
        except Exception as e:
            logger.warning(f"❌ {endpoint['name']} is down: {e}")
        return False
    
    def get_healthy_endpoint(self, model_name: Optional[str] = None) -> Optional[Dict]:
        """
        Get the best healthy endpoint based on current strategy.
        Strategies:
        - 'priority': Always pick highest priority (lowest number)
        - 'round_robin': Rotate through all healthy endpoints
        """
        # Get all candidates that are healthy AND have the model (if requested)
        candidates = []
        
        # Sort by priority first to establish a stable order
        sorted_endpoints = sorted(
            self.endpoints.items(),
            key=lambda x: x[1]['priority']
        )
        
        for name, endpoint in sorted_endpoints:
            if self.check_health(name):
                # If specific model requested, check availability
                if model_name and model_name not in endpoint['models']:
                    # Special Case: If model not found, but we are in load balance mode,
                    # we might simply skip this node.
                    continue
                candidates.append(endpoint)

        if not candidates:
            # Try to refresh health check for all endpoints as a last resort
            logger.warning("No healthy endpoints found, forcing health check refresh...")
            candidates = []
            for name, endpoint in sorted_endpoints:
                if self.check_health(name): # Force check
                     if model_name and model_name not in endpoint['models']:
                        continue
                     candidates.append(endpoint)

        if not candidates:
            logger.error("❌ No healthy endpoints available!")
            return None
            
        # Strategy: Priority (Default behavior)
        if self.strategy == 'priority':
            logger.info(f"🎯 Priority Select: {candidates[0]['name']}")
            return candidates[0]
            
        # Strategy: Round Robin
        elif self.strategy == 'round_robin':
            # Rotate index
            self.current_index = (self.current_index + 1) % len(candidates)
            selected = candidates[self.current_index]
            logger.info(f"⚖️  Load Balance: Selected {selected['name']} ({self.current_index+1}/{len(candidates)})")
            return selected
            
        return candidates[0]
    
    def generate(self, model: str, prompt: str, **kwargs) -> Optional[str]:
        """
        Generate a response using the best available endpoint.
        Automatically fails over if primary is down.
        """
        endpoint = self.get_healthy_endpoint(model)
        if not endpoint:
            return None
        
        try:
            response = requests.post(
                f"{endpoint['url']}/api/generate",
                json={
                    'model': model,
                    'prompt': prompt,
                    'stream': False,
                    **kwargs
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Got response from {endpoint['name']}")
                return result.get('response', '')
            else:
                logger.error(f"❌ Generation failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error during generation: {e}")
            # Try failover
            logger.info("🔄 Attempting failover...")
            time.sleep(self.retry_delay)
            
            # Get next endpoint
            other_endpoints = [name for name in self.endpoints if name != endpoint.get('name')]
            for fallback_name in other_endpoints:
                if self.check_health(fallback_name):
                    fallback = self.endpoints[fallback_name]
                    if model in fallback['models']:
                        logger.info(f"🔄 Failing over to {fallback['name']}")
                        return self.generate(model, prompt, **kwargs)
            
            return None
    
    def list_all_models(self) -> Dict[str, List[str]]:
        """List all available models across all healthy endpoints."""
        models = {}
        for name, endpoint in self.endpoints.items():
            if self.check_health(name):
                models[endpoint['name']] = endpoint['models']
        return models
    
    def get_status(self) -> Dict:
        """Get status of all endpoints."""
        status = {}
        for name, endpoint in self.endpoints.items():
            healthy = self.check_health(name)
            status[endpoint['name']] = {
                'healthy': healthy,
                'url': endpoint['url'],
                'models': len(endpoint['models']) if healthy else 0,
                'priority': endpoint['priority']
            }
        return status


def main():
    """Demo of the Fellowship Router."""
    print("🏰 The Fellowship AIRouter")
    print("=" * 50)
    
    router = FellowshipRouter()
    
    # Check status
    print("\n📊 Fellowship Status:")
    status = router.get_status()
    for name, info in status.items():
        health_icon = "✅" if info['healthy'] else "❌"
        print(f"{health_icon} {name}: {info['models']} models, priority {info['priority']}")
    
    # List all models
    print("\n📚 Available Models:")
    all_models = router.list_all_models()
    for endpoint_name, models in all_models.items():
        print(f"\n{endpoint_name}:")
        for model in models[:5]:  # Show first 5
            print(f"  • {model}")
        if len(models) > 5:
            print(f"  ... and {len(models) - 5} more")
    
    # Example generation (commented out to avoid actually generating)
    # response = router.generate('llama3.1:8b', 'What is 2+2?')
    # if response:
    #     print(f"\n💬 Response: {response}")


if __name__ == '__main__':
    main()
