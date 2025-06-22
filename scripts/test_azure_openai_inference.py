import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
api_key = os.environ.get("AZURE_OPENAI_KEY")
api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
deployment = os.environ.get("AZURE_OPENAI_MODEL_CHAT", "o3")

if not endpoint or not api_key:
    print("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY must be set")
    exit(1)

url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
headers = {"api-key": api_key, "Content-Type": "application/json"}
data = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2?"},
    ],
    "max_tokens": 10,
    "model": deployment,
}

print(f"Testing chat completion at: {url}")
response = requests.post(url, headers=headers, json=data)
print(f"Status code: {response.status_code}")
print("Response:")
print(response.text)