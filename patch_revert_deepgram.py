
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

ASSISTANT_ID = "2bcea4a9-6a61-488d-869c-fbda1e63af16" # Rainbow Scooty
API_KEY = os.environ.get("VAPI_PRIVATE_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def revert_stt():
    print(f"Reverting Assistant {ASSISTANT_ID} to Deepgram Nova-2...")
    url = f"https://api.vapi.ai/assistant/{ASSISTANT_ID}"
    
    payload = {
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en"
        }
    }
    
    resp = requests.patch(url, json=payload, headers=HEADERS)
    if resp.status_code == 200:
        print("✅ Success: Assistant restored to Deepgram.")
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"❌ Failed to patch: {resp.text}")

if __name__ == "__main__":
    revert_stt()
