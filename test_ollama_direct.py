from ollama import Client
from config import OLLAMA_HOST, DB_CONFIG

try:
    host = DB_CONFIG.get('host', '192.168.1.211')
    print(f"Connecting to Gandalf ({host})...")
    client = Client(host=OLLAMA_HOST)
    
    print("Listing models...")
    response = client.list()
    
    print("Models found:")
    for model in response.get('models', []):
        print(f"- {model['name']}")
        
    print("\nSuccess: Connected and listed models.")
except Exception as e:
    print(f"\nError: {e}")
