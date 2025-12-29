
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def list_numbers():
    api_key = os.environ.get("VAPI_PRIVATE_KEY")
    if not api_key:
        print("Error: VAPI_PRIVATE_KEY not set")
        return

    url = "https://api.vapi.ai/phone-number"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            numbers = response.json()
            print(f"Found {len(numbers)} numbers:")
            for num in numbers:
                print(f" - {num.get('number')} (ID: {num.get('id')})")
                print(f"   Assistant ID: {num.get('assistantId')}")
                print(f"   Provider: {num.get('provider')}")
                print("-" * 30)
        else:
            print(f"Failed to list numbers: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_numbers()
