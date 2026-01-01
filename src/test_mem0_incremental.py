#!/usr/bin/env python3
"""
Test Mem0 configuration incrementally.
"""

import sys
import os
from mem0 import Memory
from core.config import MEM0_CONFIG

def test_mem0():
    print("🧪 Testing Mem0 Configuration (Incremental)...\n")
    
    # Step 1: Initialize
    print("1️⃣ Initializing Mem0...")
    try:
        memory = Memory.from_config(MEM0_CONFIG)
        print("   ✅ Mem0 initialized!\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        print("📋 Current config:")
        import json
        print(json.dumps(MEM0_CONFIG, indent=2))
        return False
    
    # Step 2: Test add
    print("2️⃣ Testing add...")
    try:
        result = memory.add("Python is awesome", user_id="test")
        print(f"   ✅ Added: {result}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    # Step 3: Test search
    print("3️⃣ Testing search...")
    try:
        results = memory.search("programming languages", user_id="test")
        print(f"   ✅ Search results: {results}\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        return False
    
    print("✨ All tests passed!\n")
    return True

if __name__ == "__main__":
    success = test_mem0()
    sys.exit(0 if success else 1)
