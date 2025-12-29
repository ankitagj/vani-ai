
import os
import requests
import sys
from dotenv import load_dotenv

load_dotenv()

def get_assistant(assistant_id):
    api_key = os.environ.get("VAPI_PRIVATE_KEY")
    url = f"https://api.vapi.ai/assistant/{assistant_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(response.json())
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_assistant(sys.argv[1])
    else:
        print("Usage: python get_assistant_details.py <assistant_id>")
