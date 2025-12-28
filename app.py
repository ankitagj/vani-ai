from flask import Flask, request, jsonify
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

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
# Allow CORS for localhost:5173 specifically for cookie/auth if needed, or *
CORS(app) 

# Helper to read config for a specific business
def get_business_config(business_id):
    path = Path(f"businesses/{business_id}/business_config.json")
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
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
        "onboarding_status": config.get("onboarding_status", "incomplete")
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
        
        with open(biz_dir / "business_config.json", 'w') as f:
            json.dump(data, f, indent=2)
            
        # Trigger KB extraction
        from extract_qa import extract_knowledge_base
        extract_knowledge_base(business_id=biz_id)
        
        return jsonify({"success": True, "business_id": biz_id})
    except Exception as e:
        # logger.error(f"Setup error: {e}")
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
    
    for file in files:
        if file.filename == '':
            continue
            
        filename = file.filename
        raw_path = raw_dir / filename
        file.save(raw_path)
        
        try:
            logger.info(f"Processing {filename}...")
            # Process file (transcribe audio/pdf/etc)
            text_content = process_file(raw_path)
            
            # Save as standard JSON transcript
            json_content = convert_to_transcript_json(text_content, filename)
            
            # Create a safe filename for the json
            safe_name = Path(filename).stem + ".json"
            with open(transcripts_dir / safe_name, 'w') as f:
                json.dump(json_content, f, indent=2)
                
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            errors.append(f"{filename}: {str(e)}")
            
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

if __name__ == '__main__':
    print("Starting Flask server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)
