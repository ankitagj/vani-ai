
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load env vars first
load_dotenv()

# Import update function from app
from app import update_vapi_assistant, get_business_config

def sync_rd1():
    print("Syncing RD1 Voice to Vapi...")
    business_id = "rd1"
    config = get_business_config(business_id)
    assistant_id = config.get('vapi_assistant_id')
    
    if assistant_id:
        print(f"  Updating Assistant ID: {assistant_id} with new Voice ID...")
        result = update_vapi_assistant(assistant_id, business_id, config)
        if result:
            print(f"  ✅ Successfully updated RD1")
        else:
            print(f"  ❌ Failed to update RD1")
    else:
        print(f"  ⚠️ No Vapi Assistant ID found for RD1")

if __name__ == "__main__":
    sync_rd1()
