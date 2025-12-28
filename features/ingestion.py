import os
import json
import time
from pathlib import Path
from google import genai
from google.genai import types

def convert_to_transcript_json(text, filename):
    """Wraps raw text in the expected JSON format."""
    return {
        "source_file": filename,
        "transcript": text,
        "processed_at": time.time()
    }

def transcribe_audio_with_gemini(file_path, mime_type):
    """
    Uploads audio file to Gemini and requests transcription.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found")

    client = genai.Client(api_key=api_key)
    
    # 1. Upload file
    # For genai library, we might need to use the File API if the file is large, 
    # or pass bytes inline for smaller ones. 
    # Let's try passing the file content as a Part if it fits, 
    # but the safer way for audio is usually parsing it.
    
    # Actually, the google-genai library supports reading files directly or bytes.
    # We will read bytes.
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # 2. Generate Content with prompt
    prompt = "Transcribe this audio file accurately. Output ONLY the transcription text."
    
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[
            types.Content(
                parts=[
                    types.Part(text=prompt),
                    types.Part(
                        inline_data=types.Blob(
                            mime_type=mime_type,
                            data=file_bytes
                        )
                    )
                ]
            )
        ]
    )
    
    return response.text

def extract_text_from_pdf(file_path):
    """
    Uses Gemini to extract text from PDF (multimodal).
    """
    api_key = os.getenv('GEMINI_API_KEY')
    client = genai.Client(api_key=api_key)

    with open(file_path, "rb") as f:
        file_bytes = f.read()
        
    prompt = "Extract all text from this PDF document. Preserve structure where possible."
    
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[
            types.Content(
                parts=[
                    types.Part(text=prompt),
                    types.Part(
                        inline_data=types.Blob(
                            mime_type="application/pdf",
                            data=file_bytes
                        )
                    )
                ]
            )
        ]
    )
    return response.text

def process_file(file_path: Path):
    """
    Determines type and processes file. Returns the transcription/text string.
    """
    ext = file_path.suffix.lower()
    
    # Text-based
    if ext == '.json':
        # Assume it's already a transcript json or raw json
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            # If it already has 'transcript', return that.
            if isinstance(data, dict) and 'transcript' in data:
                return data['transcript']
            # If list or other dict, dump string
            return json.dumps(data, indent=2)
        except:
            return file_path.read_text(errors='replace')
            
    if ext in ['.txt', '.md', '.csv']:
        return file_path.read_text(errors='replace')

    # Audio
    if ext in ['.mp3', '.wav', '.m4a', '.ogg', '.aac']:
        # Map extension to mime (basic)
        mime_map = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav', 
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg',
            '.aac': 'audio/aac'
        }
        return transcribe_audio_with_gemini(file_path, mime_map.get(ext, 'audio/mpeg'))

    # PDF
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)

    return f"[Skipped unsupported file: {file_path.name}]"
