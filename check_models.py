import requests
from config.settings import OPENROUTER_API_KEY, OPENROUTER_BASE_URL

if not OPENROUTER_API_KEY:
    print("Error: OPENROUTER_API_KEY not found in .env")
else:
    print("--- Available OpenRouter Models ---")
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        }
        response = requests.get(f"{OPENROUTER_BASE_URL}/models", headers=headers)
        response.raise_for_status()
        models = response.json().get("data", [])
        for m in models:
            print(f"ID: {m.get('id')} | Context: {m.get('context_length', 'N/A')}")
    except Exception as e:
        print(f"Failed to list models: {e}")
