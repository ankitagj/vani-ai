
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("VAPI_PRIVATE_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
BAD_NUMBER_ID = "8f40b202-e5ec-4e5a-b430-fa1974a837bf" # +14087312233
ASSISTANT_ID = "2bcea4a9-6a61-488d-869c-fbda1e63af16" # Rainbow Scooty Assistant
BUSINESS_ID = "rainbow-scooty-training"

def release_bad_number():
    print(f"Releasing bad number: {BAD_NUMBER_ID}")
    url = f"https://api.vapi.ai/phone-number/{BAD_NUMBER_ID}"
    resp = requests.delete(url, headers=HEADERS)
    if resp.status_code == 200:
        print("✅ Number released successfully.")
    else:
        print(f"❌ Failed to release: {resp.text}")

def provision_new_number():
    print("Provisioning new number (Area Code 424)...")
    url = "https://api.vapi.ai/phone-number"
    payload = {
        "provider": "vapi",
        "numberDesiredAreaCode": "424" # Different area code to allow fresh number
    }
    resp = requests.post(url, json=payload, headers=HEADERS)
    if resp.status_code == 201:
        data = resp.json()
        new_number = data.get('number')
        new_id = data.get('id')
        print(f"✅ New Number Provisioned: {new_number} (ID: {new_id})")
        return new_number, new_id
    else:
        print(f"❌ Failed to provision: {resp.text}")
        return None, None

def bind_to_assistant(phone_id, assistant_id):
    print(f"Binding Phone {phone_id} to Assistant {assistant_id}...")
    url = f"https://api.vapi.ai/phone-number/{phone_id}"
    payload = {"assistantId": assistant_id}
    resp = requests.patch(url, json=payload, headers=HEADERS)
    if resp.status_code == 200:
        print("✅ Binding successful.")
        return True
    else:
        print(f"❌ Binding failed: {resp.text}")
        return False

def update_local_config(new_number, new_phone_id):
    path = f"businesses/{BUSINESS_ID}/business_config.json"
    print(f"Updating local config: {path}")
    try:
        with open(path, 'r') as f:
            config = json.load(f)
        
        config['deployment_phone'] = new_number
        config['vapi_phone_id'] = new_phone_id
        
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
        print("✅ Config updated.")
    except Exception as e:
        print(f"❌ Failed to update config: {e}")

if __name__ == "__main__":
    # release_bad_number() # Already done
    new_num, new_id = provision_new_number()
    if new_num and new_id:
        bind_to_assistant(new_id, ASSISTANT_ID)
        update_local_config(new_num, new_id)
