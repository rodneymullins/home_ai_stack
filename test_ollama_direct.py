from ollama import Client

try:
    print("Connecting to Thor (192.168.1.211)...")
    client = Client(host='http://192.168.1.211:11434')
    
    print("Listing models...")
    response = client.list()
    
    print("Models found:")
    for model in response.get('models', []):
        print(f"- {model['name']}")
        
    print("\nSuccess: Connected and listed models.")
except Exception as e:
    print(f"\nError: {e}")
