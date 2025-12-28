import os
import json
import glob
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

def extract_knowledge_base(business_id=None):
    """
    Reads all transcripts from businesses/{business_id}/transcripts,
    sends them to Gemini to extract a structured Knowledge Base,
    and saves the result to businesses/{business_id}/knowledge_base.json.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment.")
        return

    client = genai.Client(api_key=api_key)
    
    # 1. Determine paths
    if business_id:
        base_path = Path(f"businesses/{business_id}")
    else:
        base_path = Path(".") # Fallback for backward compatibility or root run
        
    transcripts_dir = base_path / "transcripts"
    transcript_files = glob.glob(str(transcripts_dir / "*.json"))
    
    if not transcript_files:
        print(f"❌ No transcript files found in {transcripts_dir}")
        return

    print(f"📚 Found {len(transcript_files)} transcript files in {transcripts_dir}. Loading...")
    
    all_text = ""
    for file_path in transcript_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                filename = Path(file_path).name
                content = data.get('transcript', '')
                if not content:
                    content = data.get('transcript_original', '')
                
                if content:
                    all_text += f"\n\n--- Transcript Source: {filename} ---\n{content}"
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")

    # Load Config
    config = {}
    config_path = base_path / "business_config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    
    business_name = config.get("business_name", "the business")

    print(f"📝 Total accumulated text length: {len(all_text)} characters.")

    # 2. Construct Prompt
    # We want a structured JSON output.
    prompt = f"""You are an expert knowledge engineer. Your task is to analyze the following raw call transcripts from "{business_name}" and convert them into a structured Knowledge Base.

INPUT TRANSCRIPTS:
""" + all_text + """

INSTRUCTIONS:
1. Analyze the transcripts to identify repeated customer questions and the business owner's answers.
2. EXTRACT distinct Question-Answer pairs. 
   - Generalize the question (e.g., "How much is it?" -> "What are the pricing/packages?").
   - Synthesize the BEST, most complete answer from all available information.
   - Ignore filler conversation ("Hello", "How are you", "Okay").
3. EXTRACT specific Business Facts (Entities):
   - Business Name
   - Location/Address
   - Owner Name
   - Hours of Operation
   - Contact Info
   - Services Offered
4. OUTPUT FORMAT: valid JSON only.

JSON STRUCTURE:
{
  "business_info": {
    "name": "...",
    "owner": "...",
    "phone": "...",
    "address": "...",
    "services": ["..."]
  },
  "qa_pairs": [
    {
      "category": "Pricing",
      "question": "...",
      "answer": "..."
    },
    {
      "category": "Scheduling",
      "question": "...",
      "answer": "..."
    }
    ...
  ]
}

Make sure the JSON is valid. Do not include Markdown formatting like ```json ... ```.
"""

    # 3. Call Gemini
    print("🤖 Sending to Gemini (gemini-2.0-flash-exp) for extraction...")
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[types.Content(parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        kb_content = response.text
        
        # 4. Save Output
        # Verify JSON
        try:
            parsed_kb = json.loads(kb_content)
            output_file = base_path / "knowledge_base.json"
            with open(output_file, 'w') as f:
                json.dump(parsed_kb, f, indent=2)
            print(f"✅ Knowledge Base saved to {output_file}")
            
            # Print summary
            print("\n----- EXTRACTION SUMMARY -----")
            print(f"Business: {parsed_kb.get('business_info', {}).get('name')}")
            print(f"Total Q&A Pairs: {len(parsed_kb.get('qa_pairs', []))}")
            print("------------------------------")
            
        except json.JSONDecodeError:
            print("❌ Error: Gemini output was not valid JSON.")
            print("Raw Output:", kb_content)

    except Exception as e:
        print(f"❌ Gemini API Error: {e}")

if __name__ == "__main__":
    extract_knowledge_base()
