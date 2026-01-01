#!/usr/bin/env python3
"""
Test script to verify Mem0 connection with Milvus and Ollama.
"""

import sys
from mem0 import Memory
from core.mem0_config import create_memory

def test_mem0():
    print("🧪 Testing Mem0 Setup...\n")
    
    # Initialize Mem0
    print("1️⃣ Initializing Mem0 with config...")
    try:
        memory = create_memory()
        print("   ✅ Mem0 initialized successfully\n")
    except Exception as e:
        print(f"   ❌ Failed to initialize Mem0: {e}")
        return False
    
    # Test: Save a memory
    print("2️⃣ Testing memory save...")
    try:
        test_content = "The user loves working with AI and Python programming"
        result = memory.add(test_content, user_id="test_user")
        print(f"   ✅ Memory saved: {result}\n")
    except Exception as e:
        print(f"   ❌ Failed to save memory: {e}")
        return False
    
    # Test: Recall memory
    print("3️⃣ Testing memory recall...")
    try:
        query = "What does the user like?"
        results = memory.search(query, user_id="test_user")
        print(f"   ✅ Recall successful!")
        print(f"   📋 Results: {results}\n")
    except Exception as e:
        print(f"   ❌ Failed to recall memory: {e}")
        return False
    
    # Test: Get all memories
    print("4️⃣ Testing get all memories...")
    try:
        all_memories = memory.get_all(user_id="test_user")
        print(f"   ✅ Retrieved {len(all_memories) if all_memories else 0} memories")
        if all_memories:
            print(f"   📋 Memories: {all_memories}\n")
    except Exception as e:
        print(f"   ❌ Failed to get memories: {e}")
        return False
    
    print("✨ All tests passed! Mem0 is working correctly.\n")
    return True

if __name__ == "__main__":
    success = test_mem0()
    sys.exit(0 if success else 1)
