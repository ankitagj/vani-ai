
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

ASSISTANT_ID = "2bcea4a9-6a61-488d-869c-fbda1e63af16" # Rainbow Scooty
API_KEY = os.environ.get("VAPI_PRIVATE_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# Gaurav (Indian Male) - Verified ID
INDIAN_VOICE_ID = "KKgHPEa32cUf930vw7QR" 

def patch_voice():
    print(f"Switching Assistant {ASSISTANT_ID} to Indian Voice (Gaurav)...")
    url = f"https://api.vapi.ai/assistant/{ASSISTANT_ID}"
    
    payload = {
        "voice": {
            "provider": "11labs",
            "voiceId": INDIAN_VOICE_ID
        }
    }
    
    resp = requests.patch(url, json=payload, headers=HEADERS)
    if resp.status_code == 200:
        print("✅ Success: Assistant switched to Indian Voice (Gaurav).")
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"❌ Failed to patch: {resp.text}")

if __name__ == "__main__":
    patch_voice()
