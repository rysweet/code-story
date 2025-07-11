import os
import requests

def main():
    port = os.environ.get("CODESTORY_SERVICE__PORT") or os.environ.get("PORT") or os.environ.get("CODESTORY_TEST_PORT") or "8000"
    url = f"http://localhost:{port}/"
    print(f"Testing backend root endpoint: {url}")
    try:
        resp = requests.get(url, timeout=5)
        print("Status code:", resp.status_code)
        print("Response JSON:", resp.json())
    except Exception as e:
        print("Request failed:", e)

if __name__ == "__main__":
    main()