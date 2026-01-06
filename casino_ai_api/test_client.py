#!/usr/bin/env python3
"""
Example client for testing the Casino AI API
"""

import requests
import json

API_BASE = "http://192.168.1.18:8080"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{API_BASE}/health")
    print("Health Check:", json.dumps(response.json(), indent=2))

def test_analysis():
    """Test slot analysis"""
    # Sample slot machine data
    sample_data = {
        "machines": [
            {
                "machine_id": "A-101",
                "location": "Main Floor",
                "denomination": 0.25,
                "jvi": 45.2,
                "win_rate": 87.5,
                "recent_jackpots": [1250, 980, 1500]
            },
            {
                "machine_id": "B-205",
                "location": "High Limit",
                "denomination": 5.0,
                "jvi": 67.8,
                "win_rate": 92.3,
                "recent_jackpots": [5000, 7500]
            },
            {
                "machine_id": "C-310",
                "location": "Main Floor",
                "denomination": 1.0,
                "jvi": 32.1,
                "win_rate": 78.4,
                "recent_jackpots": [850]
            }
        ],
        "analysis_type": "general"
    }
    
    response = requests.post(
        f"{API_BASE}/analyze/slots",
        json=sample_data,
        timeout=30
    )
    
    print("\nAnalysis Result:")
    result = response.json()
    print(f"\nSummary: {result['summary']}")
    print("\nKey Findings:")
    for finding in result['key_findings']:
        print(f"  - {finding}")
    print("\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  - {rec}")

if __name__ == "__main__":
    print("Testing Casino AI API...\n")
    test_health()
    print("\n" + "="*60 + "\n")
    test_analysis()
