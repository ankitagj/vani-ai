#!/usr/bin/env python3
"""
Gemini-powered query system for transcribed call recordings.
Uses transcripts as knowledge base to answer queries in English, Hindi, or Kannada.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  Google Gemini SDK not installed. Install with: pip install google-genai")


class TranscriptQueryAgent:
    """Agent that uses Gemini to answer queries based on transcribed call recordings"""
    
    def __init__(self, transcripts_dir="transcripts", api_key=None):
        """Initialize the query agent with transcript knowledge base"""
        if not GEMINI_AVAILABLE:
            raise ImportError("Google Gemini SDK is required. Install with: pip install google-genai")
        
        # Get API key
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found. Set it as environment variable or pass as argument.")
        
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.transcripts_dir = Path(transcripts_dir)
        
        # Load all transcripts
        self.transcripts = self._load_transcripts()
        print(f"📚 Loaded {len(self.transcripts)} transcript files")
        
        # Try different models in order
        self.models_to_try = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"]
        self.model_name = None
    
    def _load_transcripts(self) -> List[Dict]:
        """Load all JSON transcript files"""
        transcripts = []
        
        if not self.transcripts_dir.exists():
            print(f"⚠️  Transcripts directory not found: {self.transcripts_dir}")
            return transcripts
        
        # Find all JSON transcript files
        json_files = list(self.transcripts_dir.glob("*_gemini_*.json"))
        
        if not json_files:
            print(f"⚠️  No Gemini transcript files found in {self.transcripts_dir}")
            return transcripts
        
        for json_file in sorted(json_files):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Add filename for reference
                    data['_filename'] = json_file.name
                    transcripts.append(data)
            except Exception as e:
                print(f"⚠️  Error loading {json_file}: {e}")
        
        return transcripts
    
    def _get_transcript_context(self) -> str:
        """Format all transcripts as context for Gemini"""
        if not self.transcripts:
            return "No transcripts available."
        
        context_parts = []
        context_parts.append("=== TRANSCRIBED CALL RECORDINGS ===\n")
        context_parts.append("The following are transcriptions of business call recordings.\n")
        context_parts.append("Use this information to answer user queries.\n\n")
        
        for i, transcript in enumerate(self.transcripts, 1):
            filename = transcript.get('_filename', f'transcript_{i}')
            service = transcript.get('service', 'unknown')
            detected_lang = transcript.get('detected_language', 'unknown')
            
            context_parts.append(f"\n--- Recording {i} ({filename}) ---")
            context_parts.append(f"Service: {service}, Language: {detected_lang}\n")
            
            # Use English transcript if available, otherwise original
            transcript_text = transcript.get('transcript', '')
            if not transcript_text:
                transcript_text = transcript.get('transcript_original', '')
            
            if transcript_text:
                context_parts.append(transcript_text)
                context_parts.append("")  # Empty line between transcripts
        
        return "\n".join(context_parts)
    
    def _detect_query_language(self, query: str) -> str:
        """Detect the language of the query"""
        # Simple heuristic: check for non-ASCII characters
        has_devanagari = any('\u0900' <= c <= '\u097F' for c in query)  # Hindi
        has_kannada = any('\u0C80' <= c <= '\u0CFF' for c in query)      # Kannada
        
        if has_kannada:
            return "Kannada"
        elif has_devanagari:
            return "Hindi"
        else:
            return "English"
    
    def _initialize_model(self):
        """Initialize and test which Gemini model works"""
        if self.model_name:
            return self.model_name
        
        for model_name in self.models_to_try:
            try:
                # Test with a simple query
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=[types.Content(parts=[types.Part(text="Hello")])]
                )
                self.model_name = model_name
                print(f"✅ Using Gemini model: {model_name}")
                return model_name
            except Exception as e:
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    continue
                else:
                    # For other errors, try next model
                    continue
        
        raise Exception("No working Gemini model found. Please check your API key and quota.")
    
    def answer_query(self, query: str, language: Optional[str] = None) -> Dict:
        """Answer a query using the transcript knowledge base"""
        if not self.transcripts:
            return {
                "query": query,
                "answer": "No transcripts available. Please transcribe some call recordings first.",
                "error": "No transcripts loaded"
            }
        
        # Detect language if not provided
        if not language:
            language = self._detect_query_language(query)
        
        # Initialize model
        model_name = self._initialize_model()
        
        # Get transcript context
        context = self._get_transcript_context()
        
        # Create prompt
        prompt = f"""You are the business owner responding to customer inquiries. Answer naturally and conversationally, as if you are the business owner speaking directly to the customer.

CONTEXT FROM PREVIOUS CALL RECORDINGS:
{context}

CUSTOMER QUERY ({language}): {query}

INSTRUCTIONS:
1. Answer as the business owner would - naturally, helpfully, and directly.
2. If the query is in {language}, respond in {language} (unless the user asks in English).
3. Use ONLY the information from the call recordings above. Do NOT mention "according to recordings" or cite sources - just answer naturally.
4. If the information is not available in the transcripts, politely say you don't have that information or suggest they call for details.
5. For business queries (hours, location, pricing, services), provide clear, direct answers as a business owner would.
6. Be conversational and friendly, like you're talking to a customer on the phone.
7. If multiple recordings have the same information, use the most complete version.

Respond as the business owner:"""
        
        try:
            # Generate response
            response = self.client.models.generate_content(
                model=model_name,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=prompt)
                        ]
                    )
                ]
            )
            
            answer = response.text.strip()
            
            return {
                "query": query,
                "query_language": language,
                "answer": answer,
                "model": model_name,
                "timestamp": datetime.now().isoformat(),
                "transcripts_used": len(self.transcripts)
            }
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return {
                    "query": query,
                    "answer": "Sorry, API quota exceeded. Please try again later.",
                    "error": "quota_exceeded"
                }
            else:
                return {
                    "query": query,
                    "answer": f"Error processing query: {error_msg[:200]}",
                    "error": str(e)
                }
    
    def interactive_mode(self):
        """Run in interactive mode for querying"""
        print("\n" + "="*70)
        print("🎤 TRANSCRIPT QUERY AGENT")
        print("="*70)
        print("Ask questions about the call recordings in English, Hindi, or Kannada.")
        print("The agent will answer based on the transcribed conversations.")
        print("\nCommands:")
        print("  'quit' or 'exit' - Exit the agent")
        print("  'list' - List all loaded transcripts")
        print("  'summary' - Get a summary of all transcripts")
        print("="*70 + "\n")
        
        while True:
            try:
                query = input("\n💬 Your question: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Goodbye!")
                    break
                
                if query.lower() == 'list':
                    print("\n📚 Loaded Transcripts:")
                    for i, transcript in enumerate(self.transcripts, 1):
                        filename = transcript.get('_filename', 'unknown')
                        service = transcript.get('service', 'unknown')
                        print(f"  {i}. {filename} ({service})")
                    continue
                
                if query.lower() == 'summary':
                    print("\n📊 Transcript Summary:")
                    print(f"  Total recordings: {len(self.transcripts)}")
                    total_chars = sum(len(t.get('transcript', '')) for t in self.transcripts)
                    print(f"  Total transcript length: {total_chars:,} characters")
                    continue
                
                # Process query
                print("\n🤔 Processing your question...")
                result = self.answer_query(query)
                
                if "error" in result:
                    print(f"❌ Error: {result['answer']}")
                else:
                    print(f"\n💡 Answer ({result.get('query_language', 'unknown')}):")
                    print("-" * 70)
                    print(result['answer'])
                    print("-" * 70)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        # Interactive mode
        try:
            agent = TranscriptQueryAgent()
            agent.interactive_mode()
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            print("\nMake sure to set GEMINI_API_KEY environment variable:")
            print("  export GEMINI_API_KEY='your-api-key'")
            sys.exit(1)
    else:
        # Single query mode
        query = " ".join(sys.argv[1:])
        try:
            agent = TranscriptQueryAgent()
            result = agent.answer_query(query)
            
            if "error" in result:
                print(f"❌ Error: {result['answer']}")
                sys.exit(1)
            else:
                print(f"\n💡 Answer ({result.get('query_language', 'unknown')}):")
                print("-" * 70)
                print(result['answer'])
                print("-" * 70)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    main()

