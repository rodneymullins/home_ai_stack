#!/usr/bin/env python3
"""
Post-processor: Enriches existing memories with LLM-generated metadata.
Run this AFTER bulk ingestion to add categories/keywords.
"""

import sys
sys.path.insert(0, '/home/rod/home_ai_stack')
from src.core.mem0_config import create_memory
import requests
import json

def batch_categorize_memories(memory_texts):
    """Categorize multiple memories in one LLM call."""
    prompt = f"""Categorize these {len(memory_texts)} facts. Return JSON array only:

"""
    for i, text in enumerate(memory_texts):
        prompt += f"{i}. {text}\n"
    
    prompt += """
Return: [{"category": "...", "keywords": [...]}, ...]
Categories: finance, technology, knowledge, business
JSON:"""

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "functiongemma", "prompt": prompt, "stream": False},
            timeout=30
        )
        
        if resp.status_code == 200:
            text = resp.json().get('response', '')
            start, end = text.find('['), text.rfind(']') + 1
            if start != -1 and end > start:
                categories = json.loads(text[start:end])
                if len(categories) == len(memory_texts):
                    return categories
    except Exception as e:
        print(f"⚠️  Batch failed: {e}")
    
    return [{"category": "other", "keywords": []} for _ in memory_texts]

def main():
    print("🧠 Post-processing memories with FunctionGemma...\n")
    memory = create_memory()
    
    # Get all memories
    all_memories = memory.get_all(user_id="stock_bot")
    
    if not all_memories:
        print("No memories found!")
        return
    
    print(f"Found {len(all_memories)} memories to categorize")
    
    # Batch process in chunks of 10
    BATCH_SIZE = 10
    for i in range(0, len(all_memories), BATCH_SIZE):
        batch = all_memories[i:i+BATCH_SIZE]
        texts = [m.get('memory', '') for m in batch]
        
        print(f"Processing batch {i//BATCH_SIZE + 1}...")
        categories = batch_categorize_memories(texts)
        
        # Update each memory
        for mem, cat in zip(batch, categories):
            if 'id' in mem:
                # Update with new metadata
                current_meta = mem.get('metadata', {})
                current_meta.update(cat)
                
                try:
                    memory.update(mem['id'], data=mem.get('memory'), user_id="stock_bot", metadata=current_meta)
                    print(f"  ✓ Updated: {cat['category']}")
                except Exception as e:
                    print(f"  ✗ Failed: {e}")
    
    print("\n✅ Post-processing complete!")

if __name__ == "__main__":
    main()
