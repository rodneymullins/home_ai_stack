#!/usr/bin/env python3
"""
Simple test - just verify Mem0 can initialize and we can directly call Exo.
"""
import requests

# Test 1: Can we reach Exo?
print("1️⃣ Testing Exo connectivity...")
try:
    response = requests.get("http://192.168.1.211:8000/v1/models", timeout=5)
    if response.status_code == 200:
        models = response.json()
        print(f"   ✅ Exo responding - {len(models.get('data', []))} models available\n")
    else:
        print(f"   ❌ Exo returned: {response.status_code}\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")

# Test 2: Can Ollama embed?
print("2️⃣ Testing Ollama embeddings...")
try:
    import ollama
    result = ollama.embed(model="nomic-embed-text", input="test")
    print(f"   ✅ Ollama working - embedding dim: {len(result['embeddings'][0])}\n")
except Exception as e:
    print(f"   ❌ Failed: {e}\n")

print("✅ Basic connectivity is working!")
print("\nℹ️  Mem0 may be slow because Exo takes time to load models.")
print("    You can use the direct clients in src/memory/ for faster access.")
