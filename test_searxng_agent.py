from smolagents import CodeAgent, tool
import requests
import json

# --- 1. Define the SearXNG Tool ---
@tool
def searxng_search(query: str) -> str:
    """
    Performs a web search using the local SearXNG instance on Heimdall.
    Args:
        query: The search query string.
    """
    url = "http://192.168.1.176:8080/search"
    params = {
        "q": query,
        "format": "json"
    }
    try:
        print(f"DEBUG: Searching SearXNG for: '{query}'")
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        if not results:
            return "No results found."
        
        # Format top 3 results
        output = []
        for i, res in enumerate(results[:3]):
            title = res.get("title", "No Title")
            link = res.get("url", "No URL")
            content = res.get("content", "No content")
            output.append(f"{i+1}. {title} ({link}): {content}")
            
        return "\n\n".join(output)
    except Exception as e:
        return f"Error querying SearXNG: {e}"

# --- 2. Setup the Agent ---
# We use a lightweight model (e.g. Qwen or Llama via HuggingFace API or local if available)
# For this test, we'll try to use the 'HuggingFaceTB/SmolLM2-1.7B-Instruct' or similar free inference API 
# just to prove the logic works. usage of HfApiModel defaults to free inference if no token/url provided?
# Actually, let's use the local Ollama if possible, or just a dummy model if we just want to test the tool.
# SmolAgents needs a model. Let's try to point it to Thor's Ollama 0.0.0.0:11434 if smolagents supports it easily,
# or just use the default HfApiModel which might require a token. 
# Re-reading user context: they have standard Exo/Ollama.
# Let's use `LiteLLMModel` (if installed) or similar. 
# Simplest: Just call the tool directly to verify connectivity first, then wrap in agent if we can.

# Let's test the tool DIRECTLY first to ensure connectivity.
print("--- 1. Testing SearXNG Connectivity from Thor ---")
result = searxng_search(query="current time in New York")
print(f"Tool Output:\n{result}")

if "Error" not in result:
    print("\n✅ SearXNG is reachable and returning data!")
else:
    print("\n❌ SearXNG failed.")

# --- 3. Optional: Agents usage ---
# If you want to see an agent use it:
# from smolagents import CodeAgent, LiteLLMModel
# model = LiteLLMModel(model_id="ollama/llama3.2", api_base="http://localhost:11434")
# agent = CodeAgent(tools=[searxng_search], model=model)
# agent.run("What time is it in NY?")
