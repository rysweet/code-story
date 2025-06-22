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

if not endpoint or not api_key:
    print("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY must be set")
    exit(1)

# Remove trailing /openai if present
if endpoint.endswith("/openai"):
    endpoint = endpoint[:-7]

url = f"{endpoint}/openai/deployments?api-version={api_version}"
headers = {"api-key": api_key}

print(f"Listing deployments at: {url}")
response = requests.get(url, headers=headers)
print(f"Status code: {response.status_code}")
print("Response:")
print(response.text)