
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

ASSISTANT_ID = "2bcea4a9-6a61-488d-869c-fbda1e63af16" # Rainbow Scooty
API_KEY = os.environ.get("VAPI_PRIVATE_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def update_to_rachel():
    print(f"Updating Assistant {ASSISTANT_ID} to Rachel (American Female)...")
    url = f"https://api.vapi.ai/assistant/{ASSISTANT_ID}"
    
    # Rachel Voice ID
    payload = {
        "voice": {
            "provider": "11labs",
            "voiceId": "21m00Tcm4TlvDq8ikWAM" 
        }
    }
    
    resp = requests.patch(url, json=payload, headers=HEADERS)
    if resp.status_code == 200:
        print("✅ Successfully updated to Rachel.")
    else:
        print(f"❌ Failed to update: {resp.text}")

if __name__ == "__main__":
    update_to_rachel()
