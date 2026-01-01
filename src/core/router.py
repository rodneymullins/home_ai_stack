import requests
import json
import logging

logger = logging.getLogger(__name__)

class Router:
    def __init__(self, base_url="http://localhost:8000/v1", model="llama-3.2-1b"):
        self.base_url = base_url
        self.model = model

    def route(self, query: str) -> dict:
        """
        Route the user query using Exo (OpenAI-compatible API).
        """
        prompt = f"""You are a Router. Classify the User Input into ONE category.
        
        AGENTS:
        - "finance": Stocks, markets, prices, economy.
        - "memory": Saving facts, recalling personal info.
        - "chat": General, greetings, jokes, unknown.

        User Input: "{query}"

        Return JSON ONLY: {{"destination": "finance" | "memory" | "chat", "reason": "why"}}
        """

        try:
            # Exo uses Standard OpenAI Chat Completions API
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.0,
                    "max_tokens": 100
                    # "response_format": {"type": "json_object"} # If supported by backend, else prompt engineering
                },
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Clean Markdown code blocks if present
            if "```" in content:
                content = content.replace("```json", "").replace("```", "").strip()

            try:
                decision = json.loads(content)
                return decision
            except json.JSONDecodeError:
                logger.error(f"JSON Parse Error: {content}")
                lower = content.lower()
                if "finance" in lower: return {"destination": "finance", "reason": "Text match"}
                if "memory" in lower: return {"destination": "memory", "reason": "Text match"}
                return {"destination": "chat", "reason": "Fallback"}

        except Exception as e:
            logger.error(f"Router Error: {e}")
            return {"destination": "chat", "reason": f"Exception: {str(e)}"}

if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.INFO)
    router = Router()
    print(router.route("What is the price of Apple?"))
