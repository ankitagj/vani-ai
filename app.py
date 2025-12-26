from flask import Flask, request, jsonify
from flask_cors import CORS
# from multilingual_customer_service_agent import MultilingualCustomerServiceAgent
from query_transcripts import TranscriptQueryAgent
import logging
import requests
import os
from dotenv import load_dotenv

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
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        # Voice ID provided by user
        VOICE_ID = "g6xIsTj2HwM6VR4iXFCw"
        
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

if __name__ == '__main__':
    print("Starting Flask server on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)
