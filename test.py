import sys
import os
import requests
from urllib.parse import urljoin

"""
Usage:
  python test.py <base_url> <api_key>
Example:
  python test.py https://api.openai.com/v1 sk-xxx

This script queries the provider's `/models` endpoint directly and prints
available model IDs. Works with OpenAI-compatible APIs.
"""

def build_models_url(base_url: str) -> str:
    base = base_url.rstrip('/')
    # Most OpenAI-compatible servers expose the list at <base>/models
    return base + "/models"


def list_models(base_url: str, api_key: str):
    url = build_models_url(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return

    print(f"HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        print("Non-JSON response:")
        print(resp.text)
        return

    models = []
    for m in data.get("data", []):
        mid = m.get("id") or m.get("model")
        if mid:
            models.append(mid)

    if models:
        print("Available models:")
        for name in models:
            print(f"- {name}")
    else:
        print("No models returned or unexpected response structure:")
        print(data)


def main():
    if len(sys.argv) >= 3:
        base_url = sys.argv[1]
        api_key = sys.argv[2]
    else:
        base_url = os.environ.get("BASE_URL")
        api_key = os.environ.get("API_KEY")
    if not base_url or not api_key:
        print("Please provide base_url and api_key via args or env vars BASE_URL, API_KEY")
        sys.exit(1)
    list_models(base_url, api_key)


if __name__ == "__main__":
    main()