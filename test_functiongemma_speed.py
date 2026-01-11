#!/usr/bin/env python3
"""
FunctionGemma 270m Speed Benchmark
Test inference speed for casino AI analysis
"""
import time
import requests
import json

OLLAMA_URL = "http://192.168.1.176:11434/api/generate"
MODEL = "functiongemma:270m"

def test_speed():
    """Benchmark FunctionGemma inference speed"""
    
    # Test prompt (typical casino AI analysis)
    prompt = """Analyze this slot machine data:
    Machine: Buffalo Grand
    Recent jackpots: $1,200 (2 hours ago), $800 (5 hours ago), $1,500 (8 hours ago)
    Average interval: 3.2 hours
    Time since last: 2.1 hours
    
    Is this machine HOT, WARM, or COLD? Provide reasoning."""
    
    print("🏃 Testing FunctionGemma 270m Speed...")
    print(f"Model: {MODEL}")
    print(f"Endpoint: {OLLAMA_URL}")
    print("-" * 60)
    
    # Run 3 tests
    times = []
    for i in range(3):
        start = time.time()
        
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 150
                    }
                },
                timeout=30
            )
            
            elapsed = time.time() - start
            times.append(elapsed)
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Test {i+1}: {elapsed:.2f}s")
                print(f"   Response length: {len(data.get('response', ''))} chars")
            else:
                print(f"\n❌ Test {i+1} failed: {response.status_code}")
                
        except Exception as e:
            print(f"\n❌ Test {i+1} error: {e}")
            times.append(None)
    
    # Summary
    valid_times = [t for t in times if t is not None]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        print("\n" + "=" * 60)
        print(f"📊 RESULTS:")
        print(f"   Average inference time: {avg_time:.2f}s")
        print(f"   Min: {min(valid_times):.2f}s | Max: {max(valid_times):.2f}s")
        print(f"   ✅ Suitable for real-time dashboard: {'YES' if avg_time < 5 else 'NO'}")
        print("=" * 60)
    else:
        print("\n❌ All tests failed - check Ollama connection")

if __name__ == "__main__":
    test_speed()
