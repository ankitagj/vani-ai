import sys
import os
import logging
import json
from dotenv import load_dotenv

load_dotenv()

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("--- Starting Debug Script ---")

try:
    from query_transcripts import TranscriptQueryAgent
    
    # Initialize Agent with correct signature: business_id
    print("Initializing Agent...")
    # Use 'rainbow_default' if it exists, or None for root level
    agent = TranscriptQueryAgent(business_id="rainbow_default")
    print("Agent Initialized.")

    # Mock Message History
    history = [
        {"role": "assistant", "text": "Namaste! Welcome to Rainbow Driving School."},
    ]
    query = "What is the price?"
    
    print(f"Testing Agent with query: '{query}'")
    
    # Call the method
    response = agent.answer_query(query, history)
    
    print("--- RESPONSE RECEIVED ---")
    print(json.dumps(response, indent=2, ensure_ascii=False))

except Exception as e:
    logger.exception("An error occurred during execution")
