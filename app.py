from flask import Flask, request, jsonify, Response
from flask_cors import CORS
# from multilingual_customer_service_agent import MultilingualCustomerServiceAgent
from query_transcripts import TranscriptQueryAgent
import logging
import requests
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from leads_db import get_db

import sys
# Force UTF-8 encoding for stdout/stderr (Fixes 500 error on Hindi logging in Docker/Railway)
if sys.version_info >= (3, 7):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception as e:
        print(f"Failed to set UTF-8 encoding: {e}")

# Load environment variables
load_dotenv()
from twilio.rest import Client

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
# Allow CORS for localhost:5173 specifically for cookie/auth if needed, or *
CORS(app) 

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 160 * 1024 * 1024 # 160MB Total Request limit (to allow 15 * 10MB files)
# Note: Frontend limits individual files to 10MB. 15 files * 10MB = 150MB.

# Public URL for the backend (Ngrok) - Update this if ngrok restarts!
# Public URL for the backend
# Public URL for the backend
SERVER_URL = os.environ.get("SERVER_URL", "https://postpyloric-limnological-danika.ngrok-free.dev")
if SERVER_URL and not SERVER_URL.startswith("http"):
    SERVER_URL = f"https://{SERVER_URL}"

def provision_vapi_number(area_code='408'):
    """Provision a new phone number via Vapi API"""
    api_key = os.environ.get("VAPI_PRIVATE_KEY")
    if not api_key:
        logger.warning("VAPI_PRIVATE_KEY is missing. Cannot provision real number.")
        return None
        
    try:
        # Docs: POST https://api.vapi.ai/phone-number 
        # Url is correct.
        url = "https://api.vapi.ai/phone-number"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "provider": "vapi",
            "numberDesiredAreaCode": area_code
        }
        
        logger.info(f"Provisioning Vapi number with payload: {payload}")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"Vapi Provisioning Failed ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error provisioning Vapi number: {e}")
        return None

def create_vapi_assistant(business_id, config):
    """Create a Vapi Assistant configured for this business"""
    api_key = os.environ.get("VAPI_PRIVATE_KEY")
    if not api_key: return None
    
    agent_name = config.get('agent_name', 'Agent')
    biz_name = config.get('business_name', 'Business')
    voice_id = config.get('elevenlabs_voice_id', '21m00Tcm4TlvDq8ikWAM') # Default Rachel
    
    # Construct Server URL with business_id parameter
    # e.g. https://.../vapi/chat/completions?business_id=xyz
    # Vapi sends this to us, so we know which business context to load.
    server_url = f"{SERVER_URL}/vapi/chat/completions?business_id={business_id}"
    
    vapi_name = f"{agent_name} - {biz_name}"
    if len(vapi_name) > 40:
        vapi_name = vapi_name[:40]

    payload = {
        "name": vapi_name,
        "voice": {
            "provider": "11labs",
            "voiceId": voice_id,
        },
        "model": {
            "provider": "custom-llm",
            "model": "gpt-3.5-turbo", # Required placeholder by Vapi
            "url": server_url,
            "messages": [
                {
                    "content": f"You are {agent_name}. Act as a customer service agent for {biz_name}. If you cannot answer, refer them to {config.get('owner_name', 'the owner')} at {config.get('phone', 'our number')}.",
                    "role": "system"
                }
            ]
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en"
        },
        "serverUrl": f"{SERVER_URL}/vapi/webhook",  # CRITICAL: Destination for end-of-call-report
        "serverMessages": ["end-of-call-report"], 
        "firstMessageMode": "assistant-waits-for-user"
    }
    
    try:
        url = "https://api.vapi.ai/assistant"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        # 1. CHECK FOR DUPLICATES: prevent endless creation of same agent
        # Vapi doesn't have a direct "get by name", so we list and filter.
        # This keeps our account clean.
        try:
            list_url = "https://api.vapi.ai/assistant"
            existing_list = requests.get(list_url, headers=headers).json()
            # Depending on Vapi API, it might return a list directly or {'context': ..., 'assistants': ...}
            # Assuming list for now based on common REST patterns, checking idempotency
            target_list = existing_list if isinstance(existing_list, list) else existing_list.get('assistants', []) or []
            
            for agent in target_list:
                if agent.get('name') == vapi_name:
                    logger.info(f"♻️ Found existing Vapi agent '{vapi_name}' ({agent.get('id')}). Reusing it.")
                    # Update it to ensure new config/URL is applied
                    update_url = f"https://api.vapi.ai/assistant/{agent.get('id')}"
                    requests.patch(update_url, json=payload, headers=headers)
                    return agent, None
        except Exception as list_err:
             logger.warning(f"Failed to check existing agents: {list_err}")

        # 2. CREATE NEW if not found
        # logger.info(f"Creating Vapi Assistant with payload: {json.dumps(payload)}")
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            return response.json(), None
        else:
            error_msg = f"Vapi Error ({response.status_code}): {response.text}"
            logger.error(error_msg)
            return None, error_msg
    except Exception as e:
        logger.error(f"Error creating assistant: {e}")
        return None, str(e)

def update_vapi_assistant(assistant_id, business_id, config):
    """Update an existing Vapi Assistant"""
    api_key = os.environ.get("VAPI_PRIVATE_KEY")
    if not api_key: return None
    
    agent_name = config.get('agent_name', 'Agent')
    biz_name = config.get('business_name', 'Business')
    voice_id = config.get('elevenlabs_voice_id', '21m00Tcm4TlvDq8ikWAM')
    
    server_url = f"{SERVER_URL}/vapi/chat/completions?business_id={business_id}"
    
    vapi_name = f"{agent_name} - {biz_name}"
    if len(vapi_name) > 40:
        vapi_name = vapi_name[:40]

    payload = {
        "name": vapi_name,
        "voice": {
            "provider": "11labs",
            "voiceId": voice_id,
        },
        "model": {
            "provider": "custom-llm",
            "model": "gpt-3.5-turbo",
            "url": server_url,
            "messages": [
                {
                    "content": f"You are {agent_name}. Act as a customer service agent for {biz_name}. If you cannot answer, refer them to {config.get('owner_name', 'the owner')} at {config.get('phone', 'our number')}.",
                    "role": "system"
                }
            ]
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en"
        },
        "serverUrl": f"{SERVER_URL}/vapi/webhook",
        "serverMessages": ["end-of-call-report"], 
        "firstMessageMode": "assistant-waits-for-user"
    }
    
    try:
        url = f"https://api.vapi.ai/assistant/{assistant_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"Updating Vapi Assistant {assistant_id}...")
        response = requests.patch(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"Vapi Update Error ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error updating Vapi assistant: {e}")
        return None

def bind_vapi_number(phone_id, assistant_id):
    """Bind a phone number to an assistant"""
    api_key = os.environ.get("VAPI_PRIVATE_KEY")
    if not api_key: return False
    
    try:
        url = f"https://api.vapi.ai/phone-number/{phone_id}"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"assistantId": assistant_id}
        
        response = requests.patch(url, json=payload, headers=headers)
        return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Error binding number: {e}")
        return False

def delete_vapi_object(resource_type, object_id):
    """Delete a Vapi resource (assistant or phone-number)"""
    api_key = os.environ.get("VAPI_PRIVATE_KEY")
    if not api_key or not object_id: return False
    
    try:
        url = f"https://api.vapi.ai/{resource_type}/{object_id}"
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.delete(url, headers=headers)
        
        if response.status_code in [200, 204]:
            logger.info(f"Successfully deleted Vapi {resource_type}: {object_id}")
            return True
        else:
            logger.warning(f"Failed to delete Vapi {resource_type} {object_id}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error deleting Vapi {resource_type}: {e}")
        return False

def send_sms_greeting(to_number, business_config):
    """Send an SMS greeting via Twilio"""
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    
    # Use TWILIO_PHONE_NUMBER for SMS (purchased number)
    # If not set, can try using the sandbox number but it usually requires verification for SMS too.
    from_number = os.environ.get('TWILIO_PHONE_NUMBER')
    
    if not account_sid or not auth_token or not from_number:
        logger.warning(f"Twilio credentials or TWILIO_PHONE_NUMBER missing. Cannot send SMS. (SID={bool(account_sid)}, Token={bool(auth_token)}, Number={bool(from_number)})")
        return
        
    try:
        client = Client(account_sid, auth_token)
        
        biz_name = business_config.get('business_name', 'Our Business')
        owner_name = business_config.get('owner_name', 'The Owner')
        location = business_config.get('location', 'our office')
        contact_phone = business_config.get('phone', '')
        
        message_body = (
            f"Thanks for calling {biz_name}!\n\n"
            f"Here are our details:\n"
            f"Location: {location}\n"
            f"Owner: {owner_name} ({contact_phone})\n\n"
            f"We look forward to serving you!"
        )
        
        # Ensure to_number does NOT have whatsapp prefix, just E.164
        # Vapi usually gives +1234567890
        # If it has whatsapp: prefix (unlikely from Vapi), strip it.
        if to_number.startswith('whatsapp:'):
            to_number = to_number.replace('whatsapp:', '')
            
        message = client.messages.create(
            from_=from_number,
            body=message_body,
            to=to_number
        )
        logger.info(f"SMS sent! SID: {message.sid}")
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")

@app.route('/vapi/webhook', methods=['POST'])
def vapi_webhook_handler():
    """Handle Vapi Webhooks (e.g. end-of-call-report)"""
    try:
        data = request.json
        message = data.get('message', {})
        type_ = message.get('type')
        
        if type_ == 'end-of-call-report':
            logger.info("Received end-of-call-report")
            call = message.get('call', {})
            
            # Extract Caller Number
            # Vapi schema: call -> customer -> number
            customer = call.get('customer', {})
            caller_number = customer.get('number')
            
            # Extract Business Context via Assistant ID or other metadata
            # For simplicity, we can pass business_id in the original assistant webhook/metadata
            # OR we match the assistant ID to our folders. 
            # Let's try to extract business_id from the assistant override URL parameters if possible?
            # Actually, Vapi payloads usually include the 'assistantId'.
            # We can iterate our businesses to find which one owns this assistantId.
            # (In a real DB this is a SQL query. Here we scan files.)
            assistant_id = message.get('assistantId') or call.get('assistantId')
            
            logger.info(f"Webhook Debug - AssistantID: {assistant_id}, Caller: {caller_number}, CallID: {call.get('id')}")
            
            if assistant_id:
                # Find Business
                business = None
                businesses_dir = Path("businesses")
                if businesses_dir.exists():
                    for item in businesses_dir.iterdir():
                        if item.is_dir():
                            path = item / "business_config.json"
                            if path.exists():
                                with open(path, 'r') as f:
                                    try:
                                        cfg = json.load(f)
                                        if cfg.get('vapi_assistant_id') == assistant_id:
                                            business = cfg
                                            # Add ID to config object for downstream use
                                            business['id'] = item.name 
                                            break
                                    except: pass
                
                if business:
                    # Update conversation record with business_id if needed
                    # (logic handled in extraction worker)
                    
                    if caller_number:
                        logger.info(f"Sending SMS greeting to {caller_number}")
                        send_sms_greeting(caller_number, business)
                    else:
                        logger.info("No caller number - skipping SMS.")
                    
                    # TRIGGER ASYNC LEAD EXTRACTION
                    # We need the call ID to find the conversation
                    call_id = call.get('id')
                    if call_id:
                        logger.info(f"Triggering background lead extraction for Call ID: {call_id}")
                        # Use shared helper
                        trigger_lead_extraction(call_id, business['id'], caller_number)
                else:
                    logger.warning(f"Could not find business for assistant ID: {assistant_id}")
            
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

def trigger_lead_extraction(session_id, business_id, caller_num=None):
    """Refactored helper to trigger async lead extraction"""
    def extract_lead_worker(sid, biz_id, num):
        try:
            db = get_db()
            conv = db.get_conversation(sid)
            if not conv:
                return
            
            messages = json.loads(conv['messages'])
            if not messages:
                return
                
            agent = get_agent(biz_id)
            if not agent:
                return
                
            # Pass caller_num to prioritize physical ID
            lead_info = agent.extract_lead_info(messages, caller_number=num)
            
            # Update DB
            db.update_conversation(
                session_id=sid,
                messages=messages, 
                customer_name=lead_info.get('customer_name'),
                customer_phone=lead_info.get('customer_phone'),
                summary=lead_info.get('summary'),
                lead_classification=lead_info.get('lead_classification'),
                ended=True # For web chats, we treat every analysis as a potential "end" or just latest state
            )
            logger.info(f"Lead Extraction Complete for {sid}")
            
        except Exception as ex:
            logger.error(f"Extraction Failed: {ex}")

    import threading
    thread = threading.Thread(target=extract_lead_worker, args=(session_id, business_id, caller_num))
    thread.daemon = True
    thread.start()

# Helper to read config for a specific business
def get_business_config(business_id):
    path = Path(f"businesses/{business_id}/business_config.json")
    if path.exists():
        with open(path, 'r') as f:
            config = json.load(f)
            
        # AUTO-SYNC PHONE IF MISSING
        if not config.get('deployment_phone') and config.get('vapi_assistant_id'):
            try:
                # Lazy load check
                api_key = os.environ.get("VAPI_PRIVATE_KEY")
                if api_key:
                    assistant_id = config.get('vapi_assistant_id')
                    try:
                        p_url = "https://api.vapi.ai/phone-number"
                        p_headers = {"Authorization": f"Bearer {api_key}"}
                        p_resp = requests.get(p_url, headers=p_headers, timeout=5)
                        if p_resp.status_code == 200:
                            data = p_resp.json()
                            phones = data if isinstance(data, list) else data.get('phoneNumber', []) or []
                            # Fallback for Vapi wrapping
                            
                            found_phone = None
                            for p in phones:
                                if p.get('assistantId') == assistant_id:
                                    found_phone = p.get('number')
                                    break
                            
                            if found_phone:
                                logger.info(f"Auto-synced phone {found_phone} for {business_id}")
                                config['deployment_phone'] = found_phone
                                # Save back to file
                                with open(path, 'w') as f:
                                    json.dump(config, f, indent=2)
                    except Exception as e:
                        logger.warning(f"Auto-sync phone warning: {e}")
            except: pass # Don't crash read for this
            
        return config
    return {}

@app.route('/businesses', methods=['GET'])
def list_businesses():
    """List all available businesses"""
    businesses_dir = Path("businesses")
    if not businesses_dir.exists():
        return jsonify([])
    
    result = []
    for item in businesses_dir.iterdir():
        if item.is_dir():
            config = get_business_config(item.name)
            if config:
               result.append({
                   "id": item.name,
                   "name": config.get("business_name", item.name),
                   "location": config.get("location", "")
               })
    return jsonify(result)

@app.route('/config/<business_id>', methods=['GET'])
def get_config(business_id):
    """Serve specific config"""
    config = get_business_config(business_id)
    return jsonify({
        "agent_name": config.get("agent_name", "Assistant"),
        "business_name": config.get("business_name", "Business"),
        "greeting_message": config.get("greeting_message", "Hello! How can I help you?"),
        "onboarding_status": config.get("onboarding_status", "incomplete"),
        "deployment_phone": config.get("deployment_phone")
    })

@app.route('/setup', methods=['POST'])
def setup_business():
    """Create new business or update existing"""
    try:
        data = request.json
        biz_name = data.get('business_name', 'My Business')
        
        # Determine ID
        if not data.get('id'):
            # simple slugify
            import re
            biz_id = re.sub(r'[^a-z0-9]+', '-', biz_name.lower()).strip('-')
        else:
            biz_id = data.get('id')
            
        # Create directory structure
        biz_dir = Path(f"businesses/{biz_id}")
        (biz_dir / "transcripts").mkdir(parents=True, exist_ok=True)
        
        # Save config
        data['id'] = biz_id
        data['onboarding_status'] = 'complete'
        
        # 2a. Handle Voice Mapping
        # Use provided ID or default to Sarah (best multilingual)
        data['elevenlabs_voice_id'] = data.get('voice_id', '5Q0t7uMcjvnagumLfvZi')
            
        # 2b. Handle Phone Provisioning
        if data.get('request_new_number'):
            logger.info("Requesting new Vapi phone number...")
            prov_result = provision_vapi_number()
            if prov_result:
                # Assuming result structure has 'number' and 'id'
                new_phone = prov_result.get('number')
                vapi_phone_id = prov_result.get('id')
                
                data['deployment_phone'] = new_phone
                data['vapi_phone_id'] = vapi_phone_id
                logger.info(f"Provisioned Number: {new_phone} (ID: {vapi_phone_id})")
            else:
                logger.warning("Failed to provision number. Proceeding without it.")
        
        # 2c. Create or Update Vapi Assistant
        existing_assistant_id = None
        
        # Check if we already have an assistant for this ID
        try:
            current_config_path = biz_dir / "business_config.json"
            if current_config_path.exists():
                with open(current_config_path, 'r') as f:
                    curr_cfg = json.load(f)
                    existing_assistant_id = curr_cfg.get('vapi_assistant_id')
                    # Also preserve phone ID if not in new data
                    if not data.get('vapi_phone_id'):
                        data['vapi_phone_id'] = curr_cfg.get('vapi_phone_id')
        except Exception as e:
            logger.warning(f"Error reading existing config: {e}")

        if existing_assistant_id:
            logger.info(f"Updating existing Vapi Assistant: {existing_assistant_id}")
            assistant_result = update_vapi_assistant(existing_assistant_id, biz_id, data)
            # If update fails, we currently log it but don't hard fail.
            if not assistant_result:
                 logger.warning(f"Failed to update assistant {existing_assistant_id}")
        else:
            logger.info("Creating new Vapi Assistant...")
            assistant_result, vapi_error = create_vapi_assistant(biz_id, data)
            
            if not assistant_result:
                # CRITICAL: If creation fails, we must stop and report error
                logger.error(f"Failed to create Vapi Assistant: {vapi_error}")
                return jsonify({"error": f"Failed to create Vapi Assistant: {vapi_error}"}), 500

            assistant_id = assistant_result.get('id')
            data['vapi_assistant_id'] = assistant_id
            logger.info(f"Vapi Assistant Ready: {assistant_id}")
            
            # 2d. Bind Number if we have one
            if data.get('vapi_phone_id'):
                bind_success = bind_vapi_number(data['vapi_phone_id'], assistant_id)
                if bind_success:
                    logger.info("Successfully bound phone number to assistant.")
                else:
                     logger.error("Failed to bind phone number to assistant.")
            
            # 3. IF NO PHONE in config, try to fetch it from Vapi (Associate check)
            # This is helpful if we reused an assistant that already has a phone bound
            if not data.get('deployment_phone'):
                attempts = 0
                import time
                found_phone = None
                
                # We might need to query the phone numbers endpoint to see which one points to this assistant
                try:
                    p_url = "https://api.vapi.ai/phone-number"
                    p_headers = {"Authorization": f"Bearer {os.environ.get('VAPI_PRIVATE_KEY')}"}
                    p_resp = requests.get(p_url, headers=p_headers)
                    if p_resp.status_code == 200:
                        all_phones = p_resp.json()
                        # handle inconsistent API return (list vs dict)
                        if isinstance(all_phones, dict): all_phones = all_phones.get('phoneNumber', [])
                        
                        for p in all_phones:
                            if p.get('assistantId') == assistant_id:
                                found_phone = p.get('number')
                                found_id = p.get('id')
                                logger.info(f"📞 Found existing phone {found_phone} linked to {assistant_id}")
                                data['deployment_phone'] = found_phone
                                data['vapi_phone_id'] = found_id
                                break
                except Exception as ex:
                    logger.warning(f"Failed to fetch linked phone: {ex}")
            
        with open(biz_dir / "business_config.json", 'w') as f:
            json.dump(data, f, indent=2)
            
        # 3. Handle separate "Agent Behavior" if provided
        # We save this as a special transcript so it gets ingested into the KB logic
        agent_behavior = data.get('agent_behavior')
        if agent_behavior:
            instructions_file = biz_dir / "transcripts" / "owner_instructions.json"
            instructions_content = {
                "source": "owner_instructions",
                "transcript": f"IMPORTANT AGENT INSTRUCTIONS FROM OWNER:\n{agent_behavior}\n\nYou must align your personality and responses with these instructions.",
                "timestamp": None,
                "service": "system_instruction",
                "_filename": "owner_instructions.json"
            }
            with open(instructions_file, 'w') as f:
                json.dump(instructions_content, f, indent=2)
            
        # Trigger KB extraction (Async)
        from extract_qa import extract_knowledge_base
        import threading
        
        # Run in background so UI doesn't hang
        thread = threading.Thread(target=extract_knowledge_base, args=(biz_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True, 
            "business_id": biz_id,
            "deployment_phone": data.get('deployment_phone')
        })
    except Exception as e:
        logger.error(f"Setup error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/upload-transcripts/<business_id>', methods=['POST'])
def upload_transcripts(business_id):
    """Handle transcript file uploads for specific business with auto-ingestion"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    files = request.files.getlist('file')
    biz_dir = Path(f"businesses/{business_id}")
    transcripts_dir = biz_dir / "transcripts"
    raw_dir = biz_dir / "raw_uploads"
    
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    from features.ingestion import process_file, convert_to_transcript_json
    
    processed_count = 0
    errors = []
    
    # First save all files to disk (must be done in request context)
    saved_files = []
    for file in files:
        if file.filename == '': continue
        filename = file.filename
        raw_path = raw_dir / filename
        file.save(raw_path)
        saved_files.append((filename, raw_path))

    # Determine optimal worker count (max 5 or number of files)
    import concurrent.futures
    max_workers = min(5, len(saved_files)) if saved_files else 1
    
    processed_count = 0
    errors = []

    def process_single_file(file_info):
        f_name, f_path = file_info
        try:
            logger.info(f"Processing {f_name}...")
            # Process file (transcribe audio/pdf/etc)
            text_content = process_file(f_path)
            
            # Save as standard JSON transcript
            json_content = convert_to_transcript_json(text_content, f_name)
            
            # Create a safe filename for the json
            safe_name = Path(f_name).stem + ".json"
            with open(transcripts_dir / safe_name, 'w') as f:
                json.dump(json_content, f, indent=2)
            return True, f_name
        except Exception as e:
            logger.error(f"Error processing {f_name}: {e}")
            return False, f"{f_name}: {str(e)}"

    if saved_files:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(process_single_file, f): f for f in saved_files}
            for future in concurrent.futures.as_completed(future_to_file):
                success, result = future.result()
                if success:
                    processed_count += 1
                else:
                    errors.append(result)
            
    # Reload agent context if it's active
    if business_id in agents:
        logger.info(f"Reloading agent context for {business_id}")
        agents[business_id].reload()

    return jsonify({
        "success": True, 
        "message": f"Uploaded and processed {processed_count} files",
        "errors": errors
    }) 

@app.route('/delete-business/<business_id>', methods=['DELETE'])
def delete_business(business_id):
    """Recursively delete a business directory"""
    try:
        biz_dir = Path(f"businesses/{business_id}")
        if not biz_dir.exists():
            return jsonify({"error": "Business not found"}), 404
            
        # Cleanup Vapi Resources FIRST
        try:
            config_path = biz_dir / "business_config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                # Delete Assistant
                assistant_id = config.get('vapi_assistant_id')
                if assistant_id:
                    logger.info(f"Deleting Vapi Assistant: {assistant_id}")
                    delete_vapi_object('assistant', assistant_id)
                    
                # Delete Phone Number
                phone_id = config.get('vapi_phone_id')
                if phone_id:
                     logger.info(f"Deleting Vapi Phone: {phone_id}")
                     delete_vapi_object('phone-number', phone_id)
        except Exception as e:
            logger.error(f"Error cleaning up Vapi resources: {e}")
            # Continue to delete local files anyway
            
        import shutil
        shutil.rmtree(biz_dir)
        
        # Remove from cache if loaded
        if business_id in agents:
            del agents[business_id]
            
        logger.info(f"Deleted business: {business_id}")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error deleting business: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/knowledge-base/<business_id>', methods=['GET'])
def get_knowledge_base(business_id):
    """Get the knowledge base JSON for verification"""
    try:
        kb_path = Path(f"businesses/{business_id}/knowledge_base.json")
        if not kb_path.exists():
             return jsonify({"error": "Knowledge Base not found"}), 404
             
        with open(kb_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_api_key():
    # Try getting from env first
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key: return key
    
    # Fallback: Read from frontend/.env for dev convenience
    try:
        with open("frontend/.env", "r") as f:
            for line in f:
                if "VITE_ELEVEN_LABS_API_KEY" in line:
                    return line.split("=")[1].strip().strip('"')
    except:
        return None
    return None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the agent
# logger.info("Initializing Transcript Query Agent (Gemini)...")
# Agent Cache (Cache agents by business_id to avoid reloading)
agents = {}

def get_agent(business_id):
    if business_id not in agents:
        logger.info(f"Loading agent for {business_id}...")
        try:
            agents[business_id] = TranscriptQueryAgent(business_id=business_id, api_key=os.environ.get("GEMINI_API_KEY"))
        except Exception as e:
            logger.error(f"Failed to load agent for {business_id}: {e}")
            return None
    return agents[business_id]

@app.route('/ask-mom', methods=['POST'])
def handle_query():
    try:
        data = request.json
        # Frontend sends { "transcript": "...", "messages": [...], "business_id": "..." }
        query = data.get('transcript', '')
        messages = data.get('messages', [])
        # Default to rainbow_default if not specified (backward compat)
        business_id = data.get('business_id', 'rainbow_default')
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        agent = get_agent(business_id)
        if not agent:
             return jsonify({"error": f"Agent initialization failed for {business_id}"}), 500
        
        logger.info(f"Received query for {business_id}: {query}")
        result = agent.answer_query(query, conversation_history=messages)
        
        # Add 'response' key for compatibility
        if 'answer' in result:
            result['response'] = result['answer']

        # === DATA PERSISTENCE & ANALYTICS ===
        session_id = data.get('session_id')
        if session_id:
            try:
                db = get_db()
                existing_conv = db.get_conversation(session_id)
                
                # Append new interaction to messages
                # Messages from frontend already include history, but let's be safe
                # Actually, frontend sends FULL history. So we just update the record with latest messages + new answer.
                
                # We need to append the ASSISTANT'S response to the history before saving
                updated_messages = list(messages) 
                # (User query is already in 'messages' from frontend? 
                # No, usually frontend sends history *before* this query, or *including* this query? 
                # Standard pattern: User sends history + current query separately, or history includes current query?
                # Looking at App.tsx: handleTranscriptComplete(transcript, messages) 
                # It sends transcript AND messages. 'messages' usually implies *previous* history.
                # Let's assume 'messages' is history. We need to append User Query + Assistant Response.)
                
                # Wait, 'messages' param in App.tsx might be everything. 
                # Let's trust what Frontend sends as 'messages' is the history so far.
                # But we must add the CURRENT interaction.
                
                updated_messages.append({"role": "user", "text": query})
                updated_messages.append({"role": "assistant", "text": result['answer']})
                
                if existing_conv:
                    db.update_conversation(session_id, updated_messages)
                else:
                    db.create_conversation(session_id, language="English", business_id=business_id)
                    db.update_conversation(session_id, updated_messages) # Save messages
                
                # Trigger Analysis (Lead Extraction)
                # We trigger it on every turn for real-time updates? Or just sporadically?
                # For now, trigger every turn so dashboard updates fast.
                trigger_lead_extraction(session_id, business_id)
                
            except Exception as db_e:
                logger.error(f"DB Error in handle_query: {db_e}")

        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get-scribe-token', methods=['GET'])
def get_scribe_token():
    api_key = get_api_key()
    if not api_key:
        return jsonify({"error": "API key not found"}), 500
        
    try:
        response = requests.post(
            "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe",
            headers={"xi-api-key": api_key}
        )
        if response.status_code != 200:
            return jsonify({"error": f"ElevenLabs API error: {response.text}"}), response.status_code
            
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/tts', methods=['POST'])
def text_to_speech():
    api_key = get_api_key()
    if not api_key:
        return jsonify({"error": "API key not found"}), 500
    
    try:
        data = request.json
        text = data.get('text', '')
        language = data.get('language', 'English')  # Get language from request
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        # Voice ID provided by user
        VOICE_ID = "g6xIsTj2HwM6VR4iXFCw"
        
        # Map language to language code for better pronunciation (Hindi and English only)
        language_code_map = {
            'Hindi': 'hi',
            'English': 'en'
        }
        language_code = language_code_map.get(language, 'en')  # Default to English
        
        # Call ElevenLabs TTS API
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "language_code": language_code,  # Add language code
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            },
            stream=True
        )
        
        if response.status_code != 200:
            return jsonify({"error": f"ElevenLabs TTS error: {response.text}"}), response.status_code
            
        # Stream audio back to frontend
        from flask import Response
        return Response(response.iter_content(chunk_size=1024), content_type='audio/mpeg')
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"TTS Error: {error_msg}")
        
        # Return graceful error response
        if "quota" in error_msg.lower() or "429" in error_msg:
            return jsonify({"error": "Voice service temporarily unavailable. Please try again shortly."}), 503
        else:
            return jsonify({"error": "Unable to generate voice response. Please try again."}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "agent_status": "ready" if agent else "failed"})

@app.route('/save-conversation', methods=['POST'])
def save_conversation():
    """Save conversation and extract lead information asynchronously"""
    try:
        data = request.json
        session_id = data.get('session_id')
        messages = data.get('messages', [])
        language = data.get('language', 'English')
        business_id = data.get('business_id', 'rainbow_default')
        
        if not session_id or not messages:
            return jsonify({"error": "session_id and messages required"}), 400
        
        db = get_db()
        
        # Check if conversation exists, create if not
        existing = db.get_conversation(session_id)
        if not existing:
            db.create_conversation(session_id, language, business_id)
        
        # Save messages immediately (without lead extraction)
        db.update_conversation(
            session_id=session_id,
            messages=messages,
            ended=data.get('ended', False)
        )
        
        # Extract lead info in background thread (non-blocking)
        def extract_and_update_lead():
            try:
                # We need the correct agent for extraction
                agent = get_agent(business_id)
                if not agent:
                     logger.error(f"Cannot extract lead: agent for {business_id} not found")
                     return
                     
                lead_info = agent.extract_lead_info(messages)
                
                # Update conversation with extracted info
                db.update_conversation(
                    session_id=session_id,
                    messages=messages,
                    customer_name=lead_info.get('customer_name'),
                    customer_phone=lead_info.get('customer_phone'),
                    summary=lead_info.get('summary'),
                    lead_classification=lead_info.get('lead_classification'),
                    ended=data.get('ended', False)
                )
                
                logger.info(f"Lead extraction complete for {session_id}: {lead_info}")
            except Exception as e:
                logger.error(f"Background lead extraction failed for {session_id}: {e}")
        
        # Start background thread for lead extraction
        import threading
        thread = threading.Thread(target=extract_and_update_lead, daemon=True)
        thread.start()
        
        # Return immediately without waiting for lead extraction
        logger.info(f"Conversation saved (lead extraction in progress): {session_id}")
        
        return jsonify({
            "success": True,
            "message": "Conversation saved, lead extraction in progress"
        })
        
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard-stats')
def dashboard_stats():
    """JSON Endpoint for React Dashboard"""
    try:
        business_id = request.args.get('business_id', 'rainbow_default')
        limit = int(request.args.get('limit', 50))
        
        db = get_db()
        leads = db.get_all_conversations(limit=limit, business_id=business_id)
        
        # Calculate Stats
        stats = {
            "total_conversations": len(leads),
            "hot_leads": len([l for l in leads if l.get('lead_classification') == 'HOT_LEAD']),
            "general_inquiries": len([l for l in leads if l.get('lead_classification') == 'GENERAL_INQUIRY']),
            "spam": len([l for l in leads if l.get('lead_classification') == 'SPAM']),
            "unrelated": len([l for l in leads if l.get('lead_classification') == 'UNRELATED']),
        }
        
        return jsonify({
            "business_id": business_id,
            "stats": stats,
            "recent_conversations": leads
        })
    except Exception as e:
        logger.error(f"Dashboard Stats Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Enhanced dashboard to view captured leads with classification"""
    try:
        business_id = request.args.get('business_id', 'rainbow_default')
        config = get_business_config(business_id)
        business_name = config.get("business_name", "Business")
        
        db = get_db()
        leads = db.get_all_conversations(limit=50, business_id=business_id)
        
        # Convert to HTML table
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{business_name} - Analytics Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        h1 {{ font-size: 2em; margin-bottom: 10px; }}
        .stats {{ display: flex; gap: 20px; margin-top: 20px; }}
        .stat-card {{ background: rgba(255,255,255,0.2); padding: 15px 20px; border-radius: 8px; flex: 1; }}
        .stat-number {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ font-size: 0.9em; opacity: 0.9; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 12px; overflow: hidden; }}
        th {{ background: #4a5568; color: white; padding: 16px; text-align: left; font-weight: 600; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; }}
        td {{ padding: 16px; border-bottom: 1px solid #e2e8f0; }}
        tr:hover {{ background: #f7fafc; }}
        tr:last-child td {{ border-bottom: none; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.75em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
        .badge-hot {{ background: #fed7d7; color: #c53030; }}
        .badge-inquiry {{ background: #bee3f8; color: #2c5282; }}
        .badge-spam {{ background: #fbd38d; color: #975a16; }}
        .badge-unrelated {{ background: #e2e8f0; color: #4a5568; }}
        .phone {{ font-weight: 600; color: #2b6cb0; }}
        .name {{ font-weight: 600; color: #2d3748; }}
        .summary {{ color: #4a5568; font-size: 0.9em; line-height: 1.5; max-width: 400px; }}
        .timestamp {{ color: #718096; font-size: 0.85em; }}
        .no-data {{ text-align: center; padding: 60px; color: #a0aec0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌈 {business_name}</h1>
        <p style="font-size: 1.1em; opacity: 0.95;">Post-Call Analytics Dashboard</p>
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(leads)}</div>
                <div class="stat-label">Total Conversations</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len([l for l in leads if l.get('lead_classification') == 'HOT_LEAD'])}</div>
                <div class="stat-label">Hot Leads</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len([l for l in leads if l.get('lead_classification') == 'GENERAL_INQUIRY'])}</div>
                <div class="stat-label">General Inquiries</div>
            </div>
        </div>
    </div>
"""
        
        if not leads:
            html += '<div class="no-data">No conversations recorded yet for this business.</div>'
        else:
            html += """
    <table>
        <tr>
            <th>Date/Time</th>
            <th>Classification</th>
            <th>Customer Name</th>
            <th>Phone Number</th>
            <th>Language</th>
            <th>Conversation Summary</th>
        </tr>
"""
            
            for lead in leads:
                name = lead.get('customer_name') or '<em style="color: #a0aec0;">Not provided</em>'
                phone = lead.get('customer_phone') or '<em style="color: #a0aec0;">Not provided</em>'
                summary = lead.get('summary') or '<em style="color: #a0aec0;">No summary available</em>'
                timestamp = lead.get('created_at', '')
                language = lead.get('language', 'Unknown')
                # Use 'or' to handle None values from DB
                classification = lead.get('lead_classification') or 'UNRELATED'
                
                # Badge styling based on classification
                badge_class = {
                    'HOT_LEAD': 'badge-hot',
                    'GENERAL_INQUIRY': 'badge-inquiry',
                    'SPAM': 'badge-spam',
                    'UNRELATED': 'badge-unrelated'
                }.get(classification, 'badge-unrelated')
                
                badge_text = classification.replace('_', ' ')
                
                html += f"""
        <tr>
            <td class="timestamp">{timestamp}</td>
            <td><span class="badge {badge_class}">{badge_text}</span></td>
            <td class="name">{name}</td>
            <td class="phone">{phone}</td>
            <td>{language}</td>
            <td class="summary">{summary}</td>
        </tr>
"""
            
            html += """
    </table>
"""
        
        html += """
</body>
</html>
"""
        
        return html
        
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return f"<h1>Error loading dashboard</h1><p>{str(e)}</p>", 500

# ==========================================
# Vapi.ai / Twilio Integration Handler
# ==========================================
@app.route('/vapi/chat/completions', methods=['GET', 'POST'])
def vapi_chat_handler():
    """
    Standard OpenAI-compatible Chat Completions endpoint for Vapi.ai.
    Vapi sends the conversation history here. We use our TranscriptQueryAgent to reply.
    """
    if request.method == 'GET':
        return jsonify({"status": "ok", "message": "Vapi Endpoint Ready"}), 200

    import time
    start_time = time.time() # Start timer
    try:
        data = request.json
        stream_request = data.get('stream', False) or data.get('stream', 'false') == 'true'
        
        # Extract business_id from query params (e.g. ?business_id=xyz)
        raw_biz_id = request.args.get('business_id', 'rainbow_default')
        # Vapi/OpenAI client sometimes appends /chat/completions to the base URL query param
        business_id = raw_biz_id.split('/')[0]
        
        logger.info(f"DEBUG VAPI: Full URL: {request.url}")
        logger.info(f"DEBUG VAPI: Args: {request.args}")
        
        logger.info(f"Received Vapi Request for {business_id}: {len(data.get('messages', []))} messages. Stream={stream_request}")
        
        # 0. Get/Create DB Session
        # Vapi provides a 'call' object with 'id' in the JSON body usually, or we use a header. 
        # For robustness, we'll look for 'call' dictionary or default to a generated one if needed.
        call_id = data.get('call', {}).get('id') or data.get('call_id')
        if not call_id:
             # Fallback if Vapi doesn't send ID (unlikely)
             call_id = f"vapi-{int(time.time())}"
        
        db = get_db()
        # Check if exists, if not create
        existing = db.get_conversation(call_id)
        if not existing:
             # Create with correct business ID
             db.create_conversation(session_id=call_id, business_id=business_id, language='Hindi')
        
        # 1. Extract messages
        messages = data.get('messages', [])
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
            
        # 2. Get the latest user message
        last_message = messages[-1]
        user_query = last_message.get('content', '')
        logger.info(f"Vapi User Query: {user_query}")
        
        # Save updated history BEFORE processing (so we have the user query)
        db.update_conversation(session_id=call_id, messages=messages)

        # 3. Convert History for Agent
        formatted_history = []
        for msg in messages[:-1]:
             formatted_history.append({
                 "role": msg.get("role"),
                 "text": msg.get("content", "") 
             })

        # 3.5 Look up Caller Name for Persistent Recognition
        # Only needed if this is the start of conversation (or we want to remind the agent)
        caller_name = None
        caller_number = data.get('call', {}).get('customer', {}).get('number')
        
        # If we have a number, check DB
        if caller_number:
            known_name = db.get_customer_name(caller_number, business_id)
            if known_name:
                caller_name = known_name
                logger.info(f"Recognized caller {caller_number} as '{caller_name}'")

        # 4. Call our existing Agent Logic
        agent = get_agent(business_id) 
        
        response_data = agent.answer_query(
            query=user_query,
            conversation_history=formatted_history,
            caller_name=caller_name
        )
        
        agent_reply = response_data.get('answer', "I apologize, I'm having trouble connecting right now.")
        
        # Save the Assistant's reply to DB as well (Vapi will send it in next turn history, but nice to have now)
        # Actually Vapi ensures history consistency, so just saving 'messages' above is usually enough for the *input* state.
        # But we want to see the reply in the dashboard immediately. 
        # So we append our new reply to the list locally and save again.
        updated_messages = messages + [{"role": "assistant", "content": agent_reply}]
        db.update_conversation(session_id=call_id, messages=updated_messages)
        
        duration = time.time() - start_time
        logger.info(f"Vapi Response Generated in {duration:.2f}s: {agent_reply[:50]}...")
        
        # 5. Return Streaming Response (Server-Sent Events)
        # Even if stream=False, Vapi often works better with streaming format or at least handles it.
        # But correctly, if stream=True, we MUST stream.
        
        # Return OpenAI-compatible response
        return jsonify({
            "id": "chatcmpl-vapi-response",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "gpt-3.5-turbo",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": agent_reply
                },
                "finish_reason": "stop"
            }]
        })

    except Exception as e:
        logger.error(f"Vapi Chat Error: {e}")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"Vapi Chat Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure logging is set up to show INFO logs
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", 5002))
    print(f"Starting Flask server on port {port}...")
    # Use threaded=True for better concurrency
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
