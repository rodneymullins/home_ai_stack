
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def check_imports():
    print("Checking dependencies...")
    try:
        import mcp
        print("✅ MCP SDK found")
    except ImportError:
        print("❌ MCP SDK missing")

    try:
        import mem0
        print("✅ Mem0 found")
    except ImportError:
        print("❌ Mem0 missing")
        
    try:
        from src.core.config import MEM0_CONFIG
        print("✅ Configuration loaded")
    except ImportError as e:
        print(f"❌ Configuration error: {e}")

if __name__ == "__main__":
    check_imports()
