
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load env vars first
load_dotenv()

# Import update function from app
from app import update_vapi_assistant, get_business_config

def sync_assistants():
    print("Starting Vapi Assistant Sync...")
    
    businesses_dir = Path("businesses")
    if not businesses_dir.exists():
        print("No businesses directory found.")
        return

    count = 0
    for item in businesses_dir.iterdir():
        if item.is_dir():
            business_id = item.name
            print(f"Checking business: {business_id}")
            
            config = get_business_config(business_id)
            assistant_id = config.get('vapi_assistant_id')
            
            if assistant_id:
                print(f"  Found Assistant ID: {assistant_id}. Updating...")
                result = update_vapi_assistant(assistant_id, business_id, config)
                if result:
                    print(f"  ✅ Successfully updated {assistant_id}")
                    count += 1
                else:
                    print(f"  ❌ Failed to update {assistant_id}")
            else:
                print(f"  ⚠️ No Vapi Assistant ID in config for {business_id}")

    print(f"\nSync Complete. Updated {count} assistants.")

if __name__ == "__main__":
    sync_assistants()
