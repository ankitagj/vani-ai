from flask import Flask, request, jsonify
from flask_cors import CORS
# from multilingual_customer_service_agent import MultilingualCustomerServiceAgent
from query_transcripts import TranscriptQueryAgent
import logging
import requests
import os
from dotenv import load_dotenv
from leads_db import get_db

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
# Allow CORS for localhost:5173 specifically for cookie/auth if needed, or *
CORS(app) 

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
logger.info("Initializing Transcript Query Agent (Gemini)...")
try:
    # Initialize Gemini-powered agent
    agent = TranscriptQueryAgent(transcripts_dir="transcripts")
    logger.info("Transcript Query Agent initialized successfully!")
except Exception as e:
    logger.error(f"Failed to initialize agent: {e}")
    agent = None

@app.route('/ask-mom', methods=['POST'])
def handle_query():
    if not agent:
        return jsonify({"error": "Agent not initialized"}), 500
    
    try:
        data = request.json
        # Frontend sends { "transcript": "..." }
        query = data.get('transcript', '')
        
        if not query:
            return jsonify({"error": "No query provided"}), 400
        
        logger.info(f"Received query: {query}")
        
        # Use Gemini agent to answer
        result = agent.answer_query(query)
        
        # Add 'response' key for compatibility if anything expects it, though frontend just dumps JSON
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
                "model_id": "eleven_multilingual_v2",
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
        logger.error(f"TTS Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "agent_status": "ready" if agent else "failed"})

@app.route('/save-conversation', methods=['POST'])
def save_conversation():
    """Save conversation and extract lead information"""
    try:
        data = request.json
        session_id = data.get('session_id')
        messages = data.get('messages', [])
        language = data.get('language', 'English')
        
        if not session_id or not messages:
            return jsonify({"error": "session_id and messages required"}), 400
        
        db = get_db()
        
        # Check if conversation exists, create if not
        existing = db.get_conversation(session_id)
        if not existing:
            db.create_conversation(session_id, language)
        
        # Extract lead info using Gemini
        lead_info = agent.extract_lead_info(messages)
        
        # Update conversation with messages and extracted info
        db.update_conversation(
            session_id=session_id,
            messages=messages,
            customer_name=lead_info.get('customer_name'),
            customer_phone=lead_info.get('customer_phone'),
            summary=lead_info.get('summary'),
            ended=data.get('ended', False)
        )
        
        logger.info(f"Saved conversation {session_id}: {lead_info}")
        
        return jsonify({
            "success": True,
            "lead_info": lead_info
        })
        
    except Exception as e:
        logger.error(f"Error saving conversation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Simple dashboard to view captured leads"""
    try:
        db = get_db()
        leads = db.get_leads(limit=50)
        
        # Convert to HTML table
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Rainbow Driving School - Leads Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th { background: #4CAF50; color: white; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ddd; }
        tr:hover { background: #f9f9f9; }
        .phone { font-weight: bold; color: #2196F3; }
        .name { font-weight: bold; }
        .summary { color: #666; font-size: 0.9em; }
        .timestamp { color: #999; font-size: 0.85em; }
    </style>
</head>
<body>
    <h1>🌈 Rainbow Driving School - Customer Leads</h1>
    <p>Total Leads: """ + str(len(leads)) + """</p>
    <table>
        <tr>
            <th>Date/Time</th>
            <th>Customer Name</th>
            <th>Phone Number</th>
            <th>Language</th>
            <th>Summary</th>
        </tr>
"""
        
        for lead in leads:
            name = lead.get('customer_name') or '<em>Not provided</em>'
            phone = lead.get('customer_phone') or '<em>Not provided</em>'
            summary = lead.get('summary') or '<em>No summary</em>'
            timestamp = lead.get('created_at', '')
            language = lead.get('language', 'Unknown')
            
            html += f"""
        <tr>
            <td class="timestamp">{timestamp}</td>
            <td class="name">{name}</td>
            <td class="phone">{phone}</td>
            <td>{language}</td>
            <td class="summary">{summary}</td>
        </tr>
"""
        
        html += """
    </table>
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
