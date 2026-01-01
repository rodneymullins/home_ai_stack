import sys
import os
import time

# Ensure we can import from src
sys.path.insert(0, os.getcwd())

from src.core.router import Router

TEST_CASES = [
    ("What is the stock price of Apple?", "finance"),
    ("How is NVDA doing today?", "finance"),
    ("Analyze the market cap of Microsoft.", "finance"),
    ("Remember that I like sushi.", "memory"),
    ("What did I tell you about my car?", "memory"),
    ("Save this note: The garage code is 1234.", "memory"),
    ("Hello, how are you?", "chat"),
    ("Tell me a joke.", "chat"),
    ("Write a poem about the sea.", "chat"),
    ("Who is the president of France?", "chat"), # General knowledge -> Chat
    ("What is my wife's name?", "memory"),
    ("Buy 10 shares of GOOGL.", "finance")
]

def run_tests():
    print("🚀 Starting Router Verification (Thor: Exo - Llama 3.2 1B)...\n")
    # Using default Exo URL defined in Router class
    router = Router()
    
    correct = 0
    total = len(TEST_CASES)
    start_time = time.time()
    
    for query, expected in TEST_CASES:
        print(f"Query: '{query}'")
        try:
            t0 = time.time()
            result = router.route(query)
            duration = time.time() - t0
            
            dest = result.get("destination")
            reason = result.get("reason", "N/A")
            
            is_match = dest == expected
            icon = "✅" if is_match else "❌"
            if is_match:
                correct += 1
            
            print(f"  {icon} Predicted: {dest:<8} | Expected: {expected:<8} | Time: {duration:.3f}s")
            if not is_match:
                print(f"     Reason: {reason}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print("-" * 40)
        
    total_time = time.time() - start_time
    accuracy = (correct / total) * 100
    
    print(f"\n📊 Results:")
    print(f"Accuracy: {accuracy:.1f}% ({correct}/{total})")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Avg Latency: {total_time/total:.3f}s/query")

if __name__ == "__main__":
    run_tests()
