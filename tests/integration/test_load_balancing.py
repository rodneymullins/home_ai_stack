#!/usr/bin/env python3
import sys
import os
import logging
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from fellowship.fellowship_router import FellowshipRouter

# Configure logging to see rotation
logging.basicConfig(level=logging.INFO)

def test_round_robin():
    print("\n⚖️  Testing Round Robin Load Balancing")
    print("======================================")
    
    router = FellowshipRouter()
    
    # Mock health check to simulate both endpoints being healthy
    router.check_health = MagicMock(return_value=True)
    
    # Simulate 5 requests
    for i in range(5):
        print(f"\nRequest {i+1}:")
        endpoint = router.get_healthy_endpoint(model_name=None)
        if endpoint:
            print(f"👉 Routed to: {endpoint['name']}")
        else:
            print("❌ No healthy endpoint")

if __name__ == '__main__':
    test_round_robin()
